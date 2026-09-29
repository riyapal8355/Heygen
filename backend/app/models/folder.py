"""Folder domain model for hierarchical workspace organization."""

import uuid
from typing import List, Optional
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Folder(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Hierarchical folder scoping projects within a single workspace."""

    __tablename__ = "folders"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary scoping this folder",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Parent folder reference for nested folder trees",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Folder display name",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the folder",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    parent: Mapped[Optional["Folder"]] = relationship(
        "Folder",
        remote_side="Folder.id",
        back_populates="children",
    )
    children: Mapped[List["Folder"]] = relationship(
        "Folder",
        back_populates="parent",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="folder",
    )

    __table_args__ = (
        Index("ix_folders_workspace_parent", "workspace_id", "parent_id"),
        Index("ix_folders_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Folder id={self.id} workspace_id={self.workspace_id} name={self.name}>"
