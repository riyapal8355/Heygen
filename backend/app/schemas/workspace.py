"""Pydantic schemas for workspaces, memberships, and invitations."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.permissions import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Organization or workspace title")


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    status: Optional[str] = Field(None, description="Workspace status: active, suspended")


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = Field(None, description="Caller's role in this workspace")


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    role: str
    status: str
    joined_at: datetime


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole = Field(..., description="Updated workspace role")


class TransferOwnershipRequest(BaseModel):
    target_user_id: uuid.UUID = Field(..., description="Target member user ID to receive workspace ownership")


class WorkspaceInvitationCreate(BaseModel):
    email: str = Field(..., description="Invitee's email address")
    role: WorkspaceRole = Field(default=WorkspaceRole.CREATOR, description="Assigned role")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if "@" not in cleaned or "." not in cleaned:
            raise ValueError("Invalid email format.")
        return cleaned


class WorkspaceInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    # invitation_token is returned ONLY in non-production environments for automated testing
    invitation_token: Optional[str] = Field(
        None,
        description="Plaintext redemption token (Returned ONLY in development/testing)",
    )


class InvitationAcceptResponse(BaseModel):
    workspace: WorkspaceResponse
    role: str
    message: str


class WorkspaceRevokeResponse(BaseModel):
    """Response payload confirming invitation revocation."""
    status: str = Field(default="ok", description="Revocation status")
    message: str = Field(default="Invitation revoked successfully.", description="Status message")


class OnboardingStatusResponse(BaseModel):
    """Dynamic onboarding setup status for workspace."""
    step_1_digital_twin: bool = Field(..., description="Whether Digital Twin has been created")
    step_2_voice: bool = Field(..., description="Whether Voice has been polished/cloned")
    step_3_look: bool = Field(..., description="Whether a Look has been created")
    step_4_video: bool = Field(..., description="Whether first video project has been created")
    completed_steps: list[int] = Field(default_factory=list, description="Array of completed step numbers (1-4)")
    completed_count: int = Field(..., description="Number of completed steps (0-4)")
    total_steps: int = Field(default=4, description="Total number of setup steps")
    is_step_2_unlocked: bool = Field(..., description="Whether Step 2 is unlocked (requires Step 1)")
    is_step_3_unlocked: bool = Field(..., description="Whether Step 3 is unlocked (requires Step 1)")
    is_step_4_unlocked: bool = Field(..., description="Whether Step 4 is unlocked (requires Step 2 or 3)")


class CompleteOnboardingStepRequest(BaseModel):
    """Request payload to explicitly mark an onboarding step completed."""
    step: int = Field(..., ge=1, le=4, description="Step number (1-4) to complete")


