"""Developer API keys and Webhook domain models."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ApiKey(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Workspace-scoped developer API key."""

    __tablename__ = "api_keys"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this credential",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who generated this API key",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Human-readable label for the API key",
    )
    prefix: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Public key prefix/identifier, e.g. hz_live_a1b2c3d4",
    )
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of the secret portion",
    )
    environment: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="production",
        server_default="production",
        comment="Target environment: production or sandbox",
    )
    permissions: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="full",
        server_default="full",
        comment="Access tier: full or read_only",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
        comment="Lifecycle state: active, revoked, expired",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Optional expiration timestamp",
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp of most recent authenticated request",
    )

    # Relationships
    workspace = relationship("Workspace")
    creator = relationship("User")

    @property
    def is_active(self) -> bool:
        """Evaluate whether this key is valid and not expired."""
        if self.status != "active" or self.deleted_at is not None:
            return False
        if self.expires_at is not None:
            return datetime.now(timezone.utc) < self.expires_at
        return True

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} workspace_id={self.workspace_id} prefix={self.prefix} status={self.status}>"


class Webhook(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Workspace-scoped HTTP callback webhook registration."""

    __tablename__ = "webhooks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this webhook",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this webhook endpoint",
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Destination HTTPS/HTTP endpoint URL",
    )
    secret: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Signing secret used for HMAC-SHA256 signature",
    )
    events: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of subscribed event names",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
        comment="Endpoint state: active, disabled, revoked",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="Optional human-readable description",
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Consecutive delivery failure counter",
    )

    # Relationships
    workspace = relationship("Workspace")
    creator = relationship("User")
    deliveries = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        order_by="desc(WebhookDelivery.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Webhook id={self.id} workspace_id={self.workspace_id} url={self.url} status={self.status}>"


class WebhookDelivery(Base, UUIDPrimaryKeyMixin):
    """Audit log of an asynchronous webhook delivery attempt."""

    __tablename__ = "webhook_deliveries"

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target webhook endpoint reference",
    )
    event_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Unique event identifier for idempotency",
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Event topic, e.g. job.succeeded",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Delivered event payload",
    )
    response_status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="HTTP response status code received from destination",
    )
    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Truncated and sanitized response snippet",
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="Round-trip delivery latency in milliseconds",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="delivered",
        server_default="delivered",
        index=True,
        comment="Delivery outcome: delivered, failed, retrying",
    )
    attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Delivery attempt index (1-based)",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Error message or failure reason",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when attempt was dispatched",
    )

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery id={self.id} webhook_id={self.webhook_id} status={self.status} attempt={self.attempt}>"
