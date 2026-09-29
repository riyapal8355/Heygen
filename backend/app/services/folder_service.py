"""Folder business service enforcing hierarchy rules, cycle prevention, and non-empty deletion safety."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.folder import Folder
from app.repositories.folder import FolderRepository


class FolderService:
    """Orchestrates workspace folder operations and hierarchical invariants."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FolderRepository(db)

    async def create_folder(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        parent_id: Optional[uuid.UUID] = None,
    ) -> Folder:
        """Create folder with sibling uniqueness and parent workspace boundary checks."""
        clean_name = name.strip()
        if not clean_name:
            raise ConflictException(
                code="FOLDER_INVALID_NAME",
                message="Folder name cannot be empty.",
            )

        # 1. If parent_id provided, verify parent exists in this workspace
        if parent_id is not None:
            parent = await self.repo.get_by_id(parent_id, workspace_id)
            if not parent:
                raise NotFoundException(
                    code="FOLDER_NOT_FOUND",
                    message="Parent folder not found in this workspace.",
                )

        # 2. Prevent duplicate active sibling folder names
        if await self.repo.check_name_conflict(workspace_id, clean_name, parent_id):
            raise ConflictException(
                code="FOLDER_NAME_EXISTS",
                message=f"A folder named '{clean_name}' already exists in this location.",
            )

        folder = Folder(
            workspace_id=workspace_id,
            parent_id=parent_id,
            name=clean_name,
            created_by=user_id,
        )
        return await self.repo.create(folder)

    async def list_folders(
        self,
        workspace_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None,
        filter_parent: bool = False,
    ) -> List[Folder]:
        """List active folders scoped to workspace."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            parent_id=parent_id,
            filter_parent=filter_parent,
        )

    async def get_folder(self, folder_id: uuid.UUID, workspace_id: uuid.UUID) -> Folder:
        """Retrieve folder strictly within workspace."""
        folder = await self.repo.get_by_id(folder_id, workspace_id)
        if not folder:
            raise NotFoundException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found in this workspace.",
            )
        return folder

    async def update_folder(
        self,
        folder_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
        update_parent: bool = False,
    ) -> Folder:
        """Update folder name or move parent with cycle protection."""
        folder = await self.get_folder(folder_id, workspace_id)

        target_name = name.strip() if name is not None else folder.name
        target_parent_id = parent_id if update_parent else folder.parent_id

        # Check parent existence and cycle if parent is changing
        if update_parent and parent_id is not None:
            if parent_id == folder.id:
                raise ConflictException(
                    code="FOLDER_CYCLE_DETECTED",
                    message="A folder cannot be its own parent.",
                )
            parent = await self.repo.get_by_id(parent_id, workspace_id)
            if not parent:
                raise NotFoundException(
                    code="FOLDER_NOT_FOUND",
                    message="Target parent folder not found in this workspace.",
                )
            if await self.repo.check_cycle(folder.id, parent_id):
                raise ConflictException(
                    code="FOLDER_CYCLE_DETECTED",
                    message="Cannot move folder into one of its descendants.",
                )

        # Check name conflict in target parent
        if (target_name != folder.name) or (update_parent and target_parent_id != folder.parent_id):
            if await self.repo.check_name_conflict(workspace_id, target_name, target_parent_id, exclude_folder_id=folder.id):
                raise ConflictException(
                    code="FOLDER_NAME_EXISTS",
                    message=f"A folder named '{target_name}' already exists in the destination.",
                )

        if name is not None:
            folder.name = target_name
        if update_parent:
            folder.parent_id = target_parent_id

        return await self.repo.update(folder)

    async def delete_folder(self, folder_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        """Safely soft-delete folder, rejecting non-empty folders."""
        folder = await self.get_folder(folder_id, workspace_id)

        child_count = await self.repo.count_active_children(folder.id)
        project_count = await self.repo.count_active_projects(folder.id)

        if child_count > 0 or project_count > 0:
            raise ConflictException(
                code="FOLDER_NOT_EMPTY",
                message=f"Cannot delete folder containing {child_count} child folder(s) and {project_count} project(s).",
            )

        await self.repo.soft_delete(folder)
