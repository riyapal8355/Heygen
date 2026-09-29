"""Pydantic V2 schemas for Avatar and AvatarLook entities."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateAvatarLookRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Look display name")
    description: Optional[str] = Field(None, max_length=512)
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Pose, framing, style options")
    preview_asset_id: Optional[uuid.UUID] = Field(None, description="Look preview asset reference")
    provider: Optional[str] = Field("mock", max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)


class UpdateAvatarLookRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = Field(None, max_length=32)
    configuration: Optional[Dict[str, Any]] = None
    preview_asset_id: Optional[uuid.UUID] = None
    provider: Optional[str] = Field(None, max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)


class AvatarLookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avatar_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    configuration: Dict[str, Any]
    preview_asset_id: Optional[uuid.UUID] = None
    preview_url: Optional[str] = None
    provider: str
    provider_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateAvatarRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Avatar name")
    description: Optional[str] = Field(None, max_length=512)
    avatar_type: Optional[str] = Field("custom", max_length=32)
    visibility: Optional[str] = Field("workspace", max_length=32)
    provider: Optional[str] = Field("mock", max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)
    provider_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    preview_asset_id: Optional[uuid.UUID] = None
    source_asset_id: Optional[uuid.UUID] = None
    initial_look: Optional[CreateAvatarLookRequest] = None


class UpdateAvatarRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    avatar_type: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, max_length=32)
    visibility: Optional[str] = Field(None, max_length=32)
    provider: Optional[str] = Field(None, max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)
    provider_metadata: Optional[Dict[str, Any]] = None
    preview_asset_id: Optional[uuid.UUID] = None
    source_asset_id: Optional[uuid.UUID] = None


class AvatarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    avatar_type: str
    status: str
    visibility: str
    provider: str
    provider_reference: Optional[str] = None
    provider_metadata: Dict[str, Any]
    preview_asset_id: Optional[uuid.UUID] = None
    source_asset_id: Optional[uuid.UUID] = None
    preview_url: Optional[str] = None
    looks: List[AvatarLookResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
