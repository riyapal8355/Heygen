"""Folder repository for workspace hierarchical data operations."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder
from app.models.project import Project


class FolderRepository:
    """Encapsulates database operations for Folder entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        folder_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Folder]:
        """Fetch a single folder strictly scoped to a workspace."""
        query = select(Folder).where(
            Folder.id == folder_id,
            Folder.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(Folder.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None,
        filter_parent: bool = False,
    ) -> List[Folder]:
        """List active folders in a workspace, optionally filtered by parent_id."""
        query = select(Folder).where(
            Folder.workspace_id == workspace_id,
            Folder.deleted_at.is_(None),
        )
        if filter_parent:
            query = query.where(Folder.parent_id == parent_id)
        query = query.order_by(Folder.name.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, folder: Folder) -> Folder:
        """Persist a new folder."""
        self.db.add(folder)
        await self.db.flush()
        return folder

    async def update(self, folder: Folder) -> Folder:
        """Mark folder updated."""
        folder.updated_at = datetime.now(timezone.utc)
        self.db.add(folder)
        await self.db.flush()
        return folder

    async def soft_delete(self, folder: Folder) -> Folder:
        """Soft-delete folder with timestamp."""
        folder.deleted_at = datetime.now(timezone.utc)
        self.db.add(folder)
        await self.db.flush()
        return folder

    async def check_name_conflict(
        self,
        workspace_id: uuid.UUID,
        name: str,
        parent_id: Optional[uuid.UUID],
        exclude_folder_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Verify if another active folder in the same parent shares the requested name."""
        query = select(func.count()).select_from(Folder).where(
            Folder.workspace_id == workspace_id,
            Folder.deleted_at.is_(None),
            func.lower(Folder.name) == name.strip().lower(),
        )
        if parent_id is None:
            query = query.where(Folder.parent_id.is_(None))
        else:
            query = query.where(Folder.parent_id == parent_id)

        if exclude_folder_id:
            query = query.where(Folder.id != exclude_folder_id)

        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def count_active_children(self, folder_id: uuid.UUID) -> int:
        """Count active child folders under this folder."""
        query = select(func.count()).select_from(Folder).where(
            Folder.parent_id == folder_id,
            Folder.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_active_projects(self, folder_id: uuid.UUID) -> int:
        """Count active projects housed directly inside this folder."""
        query = select(func.count()).select_from(Project).where(
            Project.folder_id == folder_id,
            Project.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def check_cycle(self, folder_id: uuid.UUID, candidate_parent_id: uuid.UUID) -> bool:
        """Check if assigning candidate_parent_id would create an ancestor loop."""
        if folder_id == candidate_parent_id:
            return True

        current_id: Optional[uuid.UUID] = candidate_parent_id
        visited = {folder_id}

        while current_id is not None:
            if current_id in visited:
                return True
            visited.add(current_id)

            query = select(Folder.parent_id).where(Folder.id == current_id)
            res = await self.db.execute(query)
            current_id = res.scalar()

        return False
