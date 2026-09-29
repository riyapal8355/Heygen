"""Pydantic V2 schemas for Voice entity."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateVoiceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Voice display name")
    description: Optional[str] = Field(None, max_length=512)
    voice_type: Optional[str] = Field("custom", max_length=32)
    language: Optional[str] = Field("en", max_length=16)
    gender: Optional[str] = Field("neutral", max_length=16)
    provider: Optional[str] = Field("mock", max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)
    provider_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    preview_asset_id: Optional[uuid.UUID] = None
    visibility: Optional[str] = Field("workspace", max_length=32)


class UpdateVoiceRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    voice_type: Optional[str] = Field(None, max_length=32)
    language: Optional[str] = Field(None, max_length=16)
    gender: Optional[str] = Field(None, max_length=16)
    provider: Optional[str] = Field(None, max_length=64)
    provider_reference: Optional[str] = Field(None, max_length=255)
    provider_metadata: Optional[Dict[str, Any]] = None
    preview_asset_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(None, max_length=32)
    visibility: Optional[str] = Field(None, max_length=32)


class VoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    voice_type: str
    language: str
    gender: str
    provider: str
    provider_reference: Optional[str] = None
    provider_metadata: Dict[str, Any]
    preview_asset_id: Optional[uuid.UUID] = None
    preview_url: Optional[str] = None
    status: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class VoicePreviewResponse(BaseModel):
    voice_id: uuid.UUID
    preview_asset_id: Optional[uuid.UUID] = None
    preview_url: Optional[str] = None
    provider: str
    status: str
    expires_in_seconds: int = 3600
