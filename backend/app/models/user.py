"""User, UserCredential, and UserSession models."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity representing a human user across workspaces."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Normalized unique user email address",
    )
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="User's preferred display name",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        comment="User account status: active, suspended, pending",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        default=None,
        comment="Profile picture URL",
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp of most recent successful login",
    )

    # 1-to-1 relationship with isolated credentials table
    credential: Mapped[Optional["UserCredential"]] = relationship(
        "UserCredential",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1-to-many relationship with user sessions (refresh tokens)
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Memberships across workspaces
    memberships: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("email")
    def validate_and_normalize_email(self, key: str, address: str) -> str:
        """Ensure email is trimmed, lowercased, and non-empty."""
        if not address:
            raise ValueError("Email address cannot be empty.")
        cleaned = address.strip().lower()
        if "@" not in cleaned or "." not in cleaned:
            raise ValueError(f"Invalid email format: {address}")
        return cleaned

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} status={self.status}>"


class UserCredential(Base, TimestampMixin):
    """Authentication secrets isolated in a dedicated table to prevent accidental leakage."""

    __tablename__ = "user_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="Foreign key to users table",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2id cryptographic password hash",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Credential status flag",
    )

    # Relationship back to User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="credential",
    )

    def __repr__(self) -> str:
        return f"<UserCredential user_id={self.user_id} is_active={self.is_active}>"


class UserSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent session tracker storing hashed refresh tokens for secure rotation."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User to whom this session belongs",
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of the issued refresh token secret",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Client device user agent header",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Client IP address",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiration timestamp",
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when session was explicitly invalidated",
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp of last refresh usage",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )

    @property
    def is_active(self) -> bool:
        """Evaluate if session is not revoked and not expired."""
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} is_active={self.is_active}>"


# Functional index on lower(email) for case-insensitive lookup
Index("idx_users_email_lower", func.lower(User.email), unique=True)
