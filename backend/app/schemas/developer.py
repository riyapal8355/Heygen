"""Pydantic schemas for Developer API keys, Webhooks, and Deliveries."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# API Key Schemas
# =============================================================================

class ApiKeyCreateRequest(BaseModel):
    """Payload for creating a new workspace developer API key."""
    name: str = Field(..., min_length=1, max_length=128, description="Label for the API key")
    environment: Literal["production", "sandbox"] = Field("production", description="Target environment")
    permissions: Literal["full", "read_only"] = Field("full", description="Permission scope")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Optional key lifetime in days")


class ApiKeyCreatedResponse(BaseModel):
    """Response returned ONLY upon API key creation containing the one-time plaintext secret."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    prefix: str
    secret_key: str = Field(..., description="Full secret key. This value is never shown again.")
    environment: str
    permissions: str
    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyResponse(BaseModel):
    """Public metadata representation of an API key. Never includes secret or hash."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    prefix: str
    environment: str
    permissions: str
    status: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """List of API keys scoped to a workspace."""
    items: List[ApiKeyResponse]
    total: int


# =============================================================================
# Webhook Schemas
# =============================================================================

class WebhookCreateRequest(BaseModel):
    """Payload for registering a new webhook endpoint."""
    url: str = Field(..., description="Destination HTTP/HTTPS URL")
    events: List[str] = Field(
        default_factory=lambda: ["job.succeeded", "job.failed"],
        description="Subscribed event types",
    )
    description: Optional[str] = Field(None, max_length=255, description="Optional description")


class WebhookUpdateRequest(BaseModel):
    """Payload for modifying an existing webhook."""
    url: Optional[str] = Field(None, description="New destination URL")
    events: Optional[List[str]] = Field(None, description="Updated event subscriptions")
    status: Optional[Literal["active", "disabled", "revoked"]] = Field(None, description="Endpoint state")
    description: Optional[str] = Field(None, max_length=255, description="Updated description")


class WebhookCreatedResponse(BaseModel):
    """Response returned ONLY upon webhook registration containing the one-time signing secret."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    url: str
    secret: str = Field(..., description="HMAC-SHA256 signing secret. Store securely.")
    events: List[str]
    status: str
    description: Optional[str] = None
    created_at: datetime


class WebhookResponse(BaseModel):
    """Public metadata representation of a registered webhook endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    url: str
    events: List[str]
    status: str
    description: Optional[str] = None
    failure_count: int
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    """List of webhooks scoped to a workspace."""
    items: List[WebhookResponse]
    total: int


# =============================================================================
# Webhook Delivery & Event Payload Schemas
# =============================================================================

class WebhookPayload(BaseModel):
    """Standardized event payload dispatched to webhook consumers."""
    event_id: str = Field(..., description="Unique event ID for deduplication/idempotency")
    event_type: str = Field(..., description="Event topic (e.g. job.succeeded)")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace boundary")
    timestamp: str = Field(..., description="ISO 8601 UTC event generation timestamp")
    resource_id: Optional[str] = Field(None, description="Identifier of primary resource")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event body details")
    version: str = Field("v1", description="Webhook payload schema version")


class WebhookDeliveryResponse(BaseModel):
    """Log record of a webhook delivery attempt."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    webhook_id: uuid.UUID
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    latency_ms: Optional[int] = None
    status: str
    attempt: int
    error_message: Optional[str] = None
    created_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    """List of delivery attempts for a webhook."""
    items: List[WebhookDeliveryResponse]
    total: int


class WebhookTestResponse(BaseModel):
    """Response payload returned when enqueueing an integration test webhook ping."""
    status: str = Field(default="enqueued", description="Dispatch status of the test ping")
    event_id: str = Field(..., description="Unique test event identifier")
    destination_url: str = Field(..., description="Target webhook URL receiving the ping event")

