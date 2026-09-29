"""Avatar and AvatarLook domain models representing reusable digital twin and character identities."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Avatar(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Reusable avatar identity scoped to a workspace."""

    __tablename__ = "avatars"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this avatar",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the avatar",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Avatar display name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Optional human-readable description",
    )
    avatar_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="custom",
        server_default="custom",
        comment="Type: public, custom, photo, digital_twin",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
        index=True,
        comment="Status: ready, pending, training, failed, archived",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="workspace",
        server_default="workspace",
        comment="Visibility: workspace, public",
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="mock",
        server_default="mock",
        comment="AI provider engine: mock, liveportrait, sadtalker, heygen",
    )
    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Remote provider model ID or local checkpoint identifier",
    )
    provider_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible provider metadata (face bounding boxes, landmark config)",
    )
    preview_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional preview thumbnail image/video asset reference",
    )
    source_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional high-res neutral reference photo or video asset",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    preview_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[preview_asset_id])
    source_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[source_asset_id])
    looks: Mapped[List["AvatarLook"]] = relationship(
        "AvatarLook",
        back_populates="avatar",
        cascade="all, delete-orphan",
        order_by="AvatarLook.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_avatars_workspace_name", "workspace_id", "name"),
        Index("ix_avatars_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Avatar id={self.id} workspace_id={self.workspace_id} name='{self.name}' type={self.avatar_type}>"


class AvatarLook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific visual look, clothing style, or framing pose for an Avatar."""

    __tablename__ = "avatar_looks"

    avatar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("avatars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent avatar reference",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Look display name (e.g., 'Business Suit', 'Casual Studio')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Optional description of look framing or style",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready",
        server_default="ready",
        comment="Status: ready, processing, failed",
    )
    configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Look configuration (framing, pose_type: half_body, close_up, circular)",
    )
    preview_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Preview asset specific to this look",
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="mock",
        server_default="mock",
        comment="Provider used for this look",
    )
    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Look-specific provider identifier",
    )

    # Relationships
    avatar: Mapped["Avatar"] = relationship("Avatar", back_populates="looks")
    preview_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[preview_asset_id])

    __table_args__ = (
        UniqueConstraint("avatar_id", "name", name="uq_avatar_looks_avatar_name"),
        Index("ix_avatar_looks_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AvatarLook id={self.id} avatar_id={self.avatar_id} name='{self.name}'>"
