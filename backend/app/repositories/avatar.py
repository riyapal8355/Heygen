"""Avatar and AvatarLook repository for workspace-scoped data access."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.avatar import Avatar, AvatarLook


class AvatarRepository:
    """Data access operations for Workspace Avatars."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        avatar_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Avatar]:
        """Fetch avatar strictly scoped to workspace or accessible presets/public, eagerly loading its looks."""
        query = (
            select(Avatar)
            .options(selectinload(Avatar.looks))
            .where(
                Avatar.id == avatar_id,
                or_(
                    Avatar.workspace_id == workspace_id,
                    Avatar.visibility == "public",
                ),
            )
        )
        if not include_deleted:
            query = query.where(Avatar.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[Avatar]:
        """Fetch active avatar by name within workspace (case-insensitive) or public presets."""
        query = select(Avatar).where(
            or_(
                Avatar.workspace_id == workspace_id,
                Avatar.visibility == "public",
            ),
            func.lower(Avatar.name) == func.lower(name.strip()),
        )
        if not include_deleted:
            query = query.where(Avatar.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        avatar_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Avatar]:
        """List active avatars in a workspace with optional filters, including public and system presets."""
        query = (
            select(Avatar)
            .options(selectinload(Avatar.looks))
            .where(
                or_(
                    Avatar.workspace_id == workspace_id,
                    Avatar.visibility == "public",
                ),
                Avatar.deleted_at.is_(None),
            )
        )
        if avatar_type:
            query = query.where(Avatar.avatar_type == avatar_type)
        if status:
            query = query.where(Avatar.status == status)
        if search:
            query = query.where(Avatar.name.ilike(f"%{search.strip()}%"))

        query = query.order_by(Avatar.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, avatar: Avatar) -> Avatar:
        """Persist a new avatar."""
        self.db.add(avatar)
        await self.db.flush()
        return avatar

    async def update(self, avatar: Avatar) -> Avatar:
        """Mark avatar updated."""
        avatar.updated_at = datetime.now(timezone.utc)
        self.db.add(avatar)
        await self.db.flush()
        return avatar

    async def soft_delete(self, avatar: Avatar) -> Avatar:
        """Soft-delete avatar record."""
        avatar.deleted_at = datetime.now(timezone.utc)
        self.db.add(avatar)
        await self.db.flush()
        return avatar


class AvatarLookRepository:
    """Data access operations for Avatar Looks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        look_id: uuid.UUID,
        avatar_id: uuid.UUID,
    ) -> Optional[AvatarLook]:
        """Fetch look belonging to a specific avatar."""
        query = select(AvatarLook).where(
            AvatarLook.id == look_id,
            AvatarLook.avatar_id == avatar_id,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        avatar_id: uuid.UUID,
        name: str,
    ) -> Optional[AvatarLook]:
        """Check for existing look name on this avatar."""
        query = select(AvatarLook).where(
            AvatarLook.avatar_id == avatar_id,
            func.lower(AvatarLook.name) == func.lower(name.strip()),
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_avatar(self, avatar_id: uuid.UUID) -> List[AvatarLook]:
        """List all looks configured for an avatar."""
        query = (
            select(AvatarLook)
            .where(AvatarLook.avatar_id == avatar_id)
            .order_by(AvatarLook.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, look: AvatarLook) -> AvatarLook:
        """Persist a new look."""
        self.db.add(look)
        await self.db.flush()
        return look

    async def update(self, look: AvatarLook) -> AvatarLook:
        """Update look."""
        look.updated_at = datetime.now(timezone.utc)
        self.db.add(look)
        await self.db.flush()
        return look

    async def delete(self, look: AvatarLook) -> None:
        """Delete look."""
        await self.db.delete(look)
        await self.db.flush()
