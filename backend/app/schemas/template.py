"""Pydantic V2 schemas for Template and TemplateVersion entities."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TemplateVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    revision: int
    document: Dict[str, Any]
    created_by: uuid.UUID
    created_at: datetime


class CreateTemplateVersionRequest(BaseModel):
    document: Dict[str, Any] = Field(..., description="Validated template document with scenes, layers, placeholders")


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Template display name")
    description: Optional[str] = Field(None, max_length=512)
    category: Optional[str] = Field("marketing", max_length=64)
    visibility: Optional[str] = Field("workspace", max_length=32)
    thumbnail_asset_id: Optional[uuid.UUID] = None
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict)
    initial_document: Optional[Dict[str, Any]] = None


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    category: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, max_length=32)
    visibility: Optional[str] = Field(None, max_length=32)
    thumbnail_asset_id: Optional[uuid.UUID] = None
    configuration: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    category: str
    status: str
    visibility: str
    thumbnail_asset_id: Optional[uuid.UUID] = None
    configuration: Dict[str, Any]
    current_version_id: Optional[uuid.UUID] = None
    revision: int
    created_at: datetime
    updated_at: datetime
