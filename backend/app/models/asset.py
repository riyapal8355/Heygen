"""Asset domain model representing binary media files in MinIO/S3."""

import uuid
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Metadata record for binary assets persisted in object storage."""

    __tablename__ = "assets"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this asset",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who uploaded the asset",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Client-supplied filename during upload intent",
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Object storage bucket (e.g. heyzen-media)",
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        index=True,
        nullable=False,
        comment="Workspace-isolated object key in MinIO/S3",
    )
    mime_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="MIME content type (image/png, video/mp4, etc.)",
    )
    size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="File size in bytes",
    )
    checksum_sha256: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Client-claimed or server-computed SHA-256 digest",
    )
    asset_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="other",
        server_default="other",
        index=True,
        comment="Category: image, video, audio, document, font, other",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_upload",
        server_default="pending_upload",
        index=True,
        comment="Lifecycle state: pending_upload, uploaded, processing, ready, failed, deleted",
    )
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible asset metadata (dimensions, duration, codecs)",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_assets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} workspace_id={self.workspace_id} key={self.storage_key} status={self.status}>"
