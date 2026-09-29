"""Workspace, WorkspaceMember, and WorkspaceInvitation models."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import WorkspaceRole
from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Primary tenant boundary scoping all collaborative resources and permissions."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Human-readable workspace organization name",
    )
    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        comment="URL-friendly identifier unique across platform",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to the owning User",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        comment="Workspace lifecycle state: active, suspended, pending_deletion",
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
    )
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["WorkspaceInvitation"]] = relationship(
        "WorkspaceInvitation",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug} status={self.status}>"


class WorkspaceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Membership mapping associating a User with a Workspace under a designated Role."""

    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target workspace reference",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Member user reference",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkspaceRole.CREATOR.value,
        server_default=WorkspaceRole.CREATOR.value,
        comment="Assigned RBAC role: owner, admin, creator, viewer",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        comment="Membership state: active, invited, suspended",
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when member joined",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace_id={self.workspace_id} user_id={self.user_id} role={self.role}>"


class WorkspaceInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pending team invitation records securing member onboarding."""

    __tablename__ = "workspace_invitations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target workspace",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Normalized recipient email",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkspaceRole.CREATOR.value,
        server_default=WorkspaceRole.CREATOR.value,
        comment="Role granted upon acceptance",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of secret acceptance token",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="Invitation state: pending, accepted, revoked, expired",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who issued the invitation",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Expiration timestamp",
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when invitation was redeemed",
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when invitation was invalidated",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="invitations",
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    @property
    def is_valid(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.status == "pending" and self.revoked_at is None and self.expires_at > now

    def __repr__(self) -> str:
        return f"<WorkspaceInvitation id={self.id} workspace_id={self.workspace_id} email={self.email} status={self.status}>"
