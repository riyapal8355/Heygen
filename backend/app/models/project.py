"""Project and ProjectVersion domain models representing editable canvas documents."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Editable video project entity containing canvas configuration and version pointers."""

    __tablename__ = "projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this project",
    )
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional folder enclosing this project",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the project",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Project display title",
    )
    project_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="standard",
        server_default="standard",
        comment="standard, avatar_video, agent, translation, template_based",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
        comment="Lifecycle state: draft, processing, ready, archived",
    )
    aspect_ratio: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="16:9",
        server_default="16:9",
        comment="Canvas aspect ratio: 16:9, 9:16, 1:1",
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=1920,
        server_default="1920",
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=1080,
        server_default="1080",
    )
    fps: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=30,
        server_default="30",
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default="0",
    )
    thumbnail_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional thumbnail poster asset reference",
    )
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_versions.id", ondelete="SET NULL", use_alter=True, name="fk_projects_current_version_id"),
        nullable=True,
        comment="Pointer to active ProjectVersion document",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Monotonically increasing revision counter for optimistic concurrency",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="projects")
    versions: Mapped[List["ProjectVersion"]] = relationship(
        "ProjectVersion",
        back_populates="project",
        foreign_keys="ProjectVersion.project_id",
        cascade="all, delete-orphan",
    )
    current_version: Mapped[Optional["ProjectVersion"]] = relationship(
        "ProjectVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )

    __table_args__ = (
        Index("ix_projects_workspace_updated", "workspace_id", "updated_at"),
        Index("ix_projects_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} title='{self.title}' revision={self.revision} status={self.status}>"


class ProjectVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable snapshot of the complete ProjectDocument JSON at a specific revision."""

    __tablename__ = "project_versions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target project reference",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Revision number (1-indexed, immutable)",
    )
    document: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full ProjectDocument JSON payload",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who saved this revision",
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default="manual",
        comment="Source origin: manual, autosave, template, agent, import, initial",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp",
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="versions",
        foreign_keys=[project_id],
    )
    creator: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("project_id", "revision", name="uq_project_versions_project_revision"),
        Index("ix_project_versions_project_rev", "project_id", "revision"),
    )

    def __repr__(self) -> str:
        return f"<ProjectVersion id={self.id} project_id={self.project_id} rev={self.revision} source={self.source}>"
