"""Voice domain model representing speech synthesis voices, presets, and voice clones."""

import uuid
from typing import Any, Dict, Optional
from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Voice(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Speech synthesis voice definition scoped to a workspace."""

    __tablename__ = "voices"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this voice",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created or cloned the voice",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Voice display name (e.g., 'Marcus Authoritative', 'Serena Warm')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Optional description of voice tone, accent, or style",
    )
    voice_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="preset",
        server_default="preset",
        comment="Voice classification: preset, cloned, custom",
    )
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default="en",
        comment="Primary language code (ISO 639-1 or BCP 47)",
    )
    gender: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="neutral",
        server_default="neutral",
        comment="Voice perceived gender: male, female, neutral",
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="mock",
        server_default="mock",
        comment="TTS engine/provider: mock, xtts, elevenlabs, openai",
    )
    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Remote provider voice ID or local checkpoint path",
    )
    provider_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Provider configuration (pitch, speed, stability, latent weights)",
    )
    preview_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional audio sample preview asset reference in MinIO/S3",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
        index=True,
        comment="Status: ready, pending, processing, failed",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="workspace",
        server_default="workspace",
        comment="Visibility: workspace, public",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    preview_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[preview_asset_id])

    __table_args__ = (
        Index("ix_voices_workspace_name", "workspace_id", "name"),
        Index("ix_voices_workspace_lang_gender", "workspace_id", "language", "gender"),
        Index("ix_voices_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Voice id={self.id} workspace_id={self.workspace_id} name='{self.name}' lang={self.language}>"
