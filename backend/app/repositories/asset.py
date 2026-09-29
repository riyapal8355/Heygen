"""Asset repository for media catalog data access."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


class AssetRepository:
    """Data access operations for Workspace Assets."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        asset_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Asset]:
        """Fetch asset strictly scoped to workspace or accessible system catalog presets."""
        from app.db.seeds import SYSTEM_WORKSPACE_ID
        query = select(Asset).where(
            Asset.id == asset_id,
            or_(
                Asset.workspace_id == workspace_id,
                Asset.workspace_id == SYSTEM_WORKSPACE_ID,
            ),
        )
        if not include_deleted:
            query = query.where(Asset.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Asset]:
        """List active workspace assets with optional filters."""
        query = select(Asset).where(
            Asset.workspace_id == workspace_id,
            Asset.deleted_at.is_(None),
        )

        if asset_type:
            query = query.where(Asset.asset_type == asset_type)

        if status:
            query = query.where(Asset.status == status)

        if search:
            query = query.where(Asset.original_filename.ilike(f"%{search.strip()}%"))

        query = query.order_by(Asset.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, asset: Asset) -> Asset:
        """Persist a new asset."""
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def update(self, asset: Asset) -> Asset:
        """Mark asset updated."""
        asset.updated_at = datetime.now(timezone.utc)
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def soft_delete(self, asset: Asset) -> Asset:
        """Soft-delete asset record."""
        asset.deleted_at = datetime.now(timezone.utc)
        asset.status = "deleted"
        self.db.add(asset)
        await self.db.flush()
        return asset
