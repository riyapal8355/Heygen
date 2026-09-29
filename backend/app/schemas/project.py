"""Pydantic schemas for Project and Project Version lifecycle management."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_document import ProjectDocumentV1


class ProjectCreate(BaseModel):
    """Payload for creating a new editable Project."""
    title: str = Field(..., min_length=1, max_length=255, description="Project title")
    folder_id: Optional[uuid.UUID] = Field(default=None, description="Optional target folder UUID")
    project_type: str = Field(default="standard", description="standard, avatar_video, agent, translation, template_based")
    aspect_ratio: str = Field(default="16:9", description="16:9, 9:16, 1:1")
    width: int = Field(default=1920, ge=128, le=7680)
    height: int = Field(default=1080, ge=128, le=4320)
    fps: int = Field(default=30, ge=1, le=120)


class ProjectUpdate(BaseModel):
    """Payload for updating project metadata."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    folder_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default=None, description="draft, processing, ready, archived")
    aspect_ratio: Optional[str] = None
    thumbnail_asset_id: Optional[uuid.UUID] = None


class ProjectResponse(BaseModel):
    """Public project summary representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    folder_id: Optional[uuid.UUID] = None
    created_by: uuid.UUID
    title: str
    project_type: str
    status: str
    aspect_ratio: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    duration_ms: Optional[int] = None
    thumbnail_asset_id: Optional[uuid.UUID] = None
    current_version_id: Optional[uuid.UUID] = None
    revision: int
    created_at: datetime
    updated_at: datetime


class ProjectVersionResponse(BaseModel):
    """Immutable version snapshot containing the complete ProjectDocument."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    revision: int
    document: Union[ProjectDocumentV1, Dict[str, Any]] = Field(..., description="Project document snapshot")
    source: str
    created_by: uuid.UUID
    created_at: datetime



class CreateProjectVersionRequest(BaseModel):
    """Optimistic concurrency save request requiring matching expected_revision."""
    expected_revision: int = Field(..., description="Current revision caller expects to update")
    document: ProjectDocumentV1 = Field(..., description="Validated ProjectDocumentV1 payload")
    source: Optional[str] = Field(default="manual", description="manual, autosave, template, agent, import")
