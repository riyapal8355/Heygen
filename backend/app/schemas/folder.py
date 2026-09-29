"""Pydantic schemas for Workspace Folder management."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    """Payload for creating a new folder in a workspace."""
    name: str = Field(..., min_length=1, max_length=128, description="Folder display name")
    parent_id: Optional[uuid.UUID] = Field(default=None, description="Optional parent folder UUID")


class FolderUpdate(BaseModel):
    """Payload for updating an existing folder."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128, description="Updated name")
    parent_id: Optional[uuid.UUID] = Field(default=None, description="New parent folder UUID for moves")


class FolderResponse(BaseModel):
    """Public folder representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
