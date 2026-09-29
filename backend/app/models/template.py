"""Template and TemplateVersion domain models representing reusable project starters and immutable snapshots."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Template(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Reusable project blueprint and starting canvas document."""

    __tablename__ = "templates"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this template",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the template",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Template display title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Template overview and intended use case",
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="marketing",
        server_default="marketing",
        index=True,
        comment="Category: marketing, sales, onboarding, education, social",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
        comment="Status: active, draft, archived",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="workspace",
        server_default="workspace",
        comment="Visibility: workspace, public",
    )
    thumbnail_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Poster preview thumbnail asset reference",
    )
    configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible configuration (aspect_ratio, placeholders schema, tags)",
    )
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("template_versions.id", ondelete="SET NULL", use_alter=True, name="fk_templates_current_version_id"),
        nullable=True,
        comment="Pointer to current active immutable template document snapshot",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Active revision sequence number",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    thumbnail_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[thumbnail_asset_id])
    versions: Mapped[List["TemplateVersion"]] = relationship(
        "TemplateVersion",
        back_populates="template",
        foreign_keys="TemplateVersion.template_id",
        cascade="all, delete-orphan",
        order_by="TemplateVersion.revision.asc()",
    )
    current_version: Mapped[Optional["TemplateVersion"]] = relationship(
        "TemplateVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )

    __table_args__ = (
        Index("ix_templates_workspace_name", "workspace_id", "name"),
        Index("ix_templates_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} workspace_id={self.workspace_id} name='{self.name}' rev={self.revision}>"


class TemplateVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable snapshot of a Template's structured document at a specific revision."""

    __tablename__ = "template_versions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent template reference",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Immutable revision sequence number",
    )
    document: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full validated template document payload (scenes, layers, placeholders)",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who created this version snapshot",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Snapshot creation timestamp",
    )

    # Relationships
    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="versions",
        foreign_keys=[template_id],
    )
    creator: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("template_id", "revision", name="uq_template_versions_template_revision"),
        Index("ix_template_versions_template_rev", "template_id", "revision"),
    )

    def __repr__(self) -> str:
        return f"<TemplateVersion id={self.id} template_id={self.template_id} rev={self.revision}>"
