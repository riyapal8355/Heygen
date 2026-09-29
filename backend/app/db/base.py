"""Declarative base and reusable model mixins for SQLAlchemy 2.x."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all HeyZen domain models."""
    pass


class UUIDPrimaryKeyMixin:
    """Provides a sequential / random UUIDv4 primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-100,
    )


class TimestampMixin:
    """Provides timezone-aware creation and update timestamps in UTC."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Provides optional soft-delete timestamp.
    
    Only apply to entities that require user-facing recovery grace periods
    (e.g., projects, folders, assets). Do NOT apply to all tables.
    """
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
