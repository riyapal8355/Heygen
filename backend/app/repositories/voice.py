"""Voice repository for workspace-scoped audio voice data access."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice import Voice


class VoiceRepository:
    """Data access operations for Workspace Voices."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        voice_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Voice]:
        """Fetch voice strictly scoped to workspace or accessible presets/public."""
        query = select(Voice).where(
            Voice.id == voice_id,
            or_(
                Voice.workspace_id == workspace_id,
                Voice.visibility == "public",
            ),
        )
        if not include_deleted:
            query = query.where(Voice.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[Voice]:
        """Fetch voice by name within workspace (case-insensitive)."""
        query = select(Voice).where(
            Voice.workspace_id == workspace_id,
            func.lower(Voice.name) == func.lower(name.strip()),
        )
        if not include_deleted:
            query = query.where(Voice.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        voice_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Voice]:
        """List active voices in a workspace with optional filters, including presets and public voices."""
        query = select(Voice).where(
            or_(
                Voice.workspace_id == workspace_id,
                Voice.visibility == "public",
            ),
            Voice.deleted_at.is_(None),
        )
        if language:
            query = query.where(Voice.language == language)
        if gender:
            query = query.where(Voice.gender == gender)
        if voice_type:
            query = query.where(Voice.voice_type == voice_type)
        if status:
            query = query.where(Voice.status == status)
        if search:
            query = query.where(Voice.name.ilike(f"%{search.strip()}%"))

        query = query.order_by(Voice.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, voice: Voice) -> Voice:
        """Persist a new voice."""
        self.db.add(voice)
        await self.db.flush()
        return voice

    async def update(self, voice: Voice) -> Voice:
        """Mark voice updated."""
        voice.updated_at = datetime.now(timezone.utc)
        self.db.add(voice)
        await self.db.flush()
        return voice

    async def soft_delete(self, voice: Voice) -> Voice:
        """Soft-delete voice record."""
        voice.deleted_at = datetime.now(timezone.utc)
        self.db.add(voice)
        await self.db.flush()
        return voice
