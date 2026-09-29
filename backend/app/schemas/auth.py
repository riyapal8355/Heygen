"""Pydantic schemas for authentication and user sessions."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignupRequest(BaseModel):
    email: str = Field(..., description="Valid user email address")
    display_name: str = Field(..., min_length=2, max_length=128, description="User's display name")
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if "@" not in cleaned or "." not in cleaned:
            raise ValueError("Invalid email format.")
        return cleaned


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered user email")
    password: str = Field(..., description="User password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if "@" not in cleaned or "." not in cleaned:
            raise ValueError("Invalid email format.")
        return cleaned


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Optional refresh token if cookie is not available")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    status: str
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class WorkspaceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    role: str


class AuthResponse(BaseModel):
    user: UserResponse
    workspace: Optional[WorkspaceSummary] = None
    tokens: TokenResponse


class UserWithWorkspacesResponse(BaseModel):
    user: UserResponse
    workspaces: List[WorkspaceSummary]


class LogoutResponse(BaseModel):
    """Response payload confirming user session termination."""
    status: str = Field(default="ok", description="Status confirmation")
    message: str = Field(default="Logged out successfully.", description="Logout message")

