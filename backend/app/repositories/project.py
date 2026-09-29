"""Project and ProjectVersion repository for transactional canvas operations."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectVersion


class ProjectRepository:
    """Data access repository for Projects and immutable ProjectVersions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Project]:
        """Fetch project strictly scoped to a workspace."""
        query = select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(Project.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_for_update(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[Project]:
        """Fetch project row with an exclusive row-level lock (FOR UPDATE)."""
        query = (
            select(Project)
            .where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.deleted_at.is_(None),
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        folder_id: Optional[uuid.UUID] = None,
        filter_folder: bool = False,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Project]:
        """List active projects in a workspace with optional filters."""
        query = select(Project).where(
            Project.workspace_id == workspace_id,
            Project.deleted_at.is_(None),
        )

        if filter_folder:
            if folder_id is None:
                query = query.where(Project.folder_id.is_(None))
            else:
                query = query.where(Project.folder_id == folder_id)

        if status:
            query = query.where(Project.status == status)

        if search:
            query = query.where(Project.title.ilike(f"%{search.strip()}%"))

        query = query.order_by(Project.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        folder_id: Optional[uuid.UUID] = None,
        filter_folder: bool = False,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count active projects matching query filters."""
        query = select(func.count()).select_from(Project).where(
            Project.workspace_id == workspace_id,
            Project.deleted_at.is_(None),
        )

        if filter_folder:
            if folder_id is None:
                query = query.where(Project.folder_id.is_(None))
            else:
                query = query.where(Project.folder_id == folder_id)

        if status:
            query = query.where(Project.status == status)

        if search:
            query = query.where(Project.title.ilike(f"%{search.strip()}%"))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create_project_with_initial_version(
        self,
        project: Project,
        initial_version: ProjectVersion,
    ) -> Project:
        """Atomically create Project and initial ProjectVersion revision 1."""
        self.db.add(project)
        await self.db.flush()

        initial_version.project_id = project.id
        self.db.add(initial_version)
        await self.db.flush()

        project.current_version_id = initial_version.id
        self.db.add(project)
        await self.db.flush()
        return project

    async def update(self, project: Project) -> Project:
        """Mark project updated."""
        project.updated_at = datetime.now(timezone.utc)
        self.db.add(project)
        await self.db.flush()
        return project

    async def soft_delete(self, project: Project) -> Project:
        """Soft-delete project."""
        project.deleted_at = datetime.now(timezone.utc)
        self.db.add(project)
        await self.db.flush()
        return project

    async def create_version(self, version: ProjectVersion) -> ProjectVersion:
        """Insert a new immutable project version snapshot."""
        self.db.add(version)
        await self.db.flush()
        return version

    async def update_version(self, version: ProjectVersion) -> ProjectVersion:
        """Update an existing project version snapshot."""
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_version_by_id(
        self,
        version_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Optional[ProjectVersion]:
        """Fetch specific immutable version snapshot."""
        query = select(ProjectVersion).where(
            ProjectVersion.id == version_id,
            ProjectVersion.project_id == project_id,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_versions(
        self,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ProjectVersion]:
        """List historical version snapshots descending by revision."""
        query = (
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.revision.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
