"""Project business service managing editable canvas workflows and optimistic concurrency."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.project import Project, ProjectVersion
from app.repositories.asset import AssetRepository
from app.repositories.folder import FolderRepository
from app.repositories.project import ProjectRepository
from app.schemas.project_document import ProjectDocumentV1, create_default_project_document


class ProjectService:
    """Manages Project entities, initial canvas setup, and concurrency-controlled versions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.folder_repo = FolderRepository(db)
        self.asset_repo = AssetRepository(db)

    async def create_project(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        folder_id: Optional[uuid.UUID] = None,
        project_type: str = "standard",
        aspect_ratio: str = "16:9",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> Project:
        """Create a new project and initialize it with revision 1 ProjectDocumentV1."""
        clean_title = title.strip()
        if not clean_title:
            raise ConflictException(
                code="PROJECT_INVALID_TITLE",
                message="Project title cannot be empty.",
            )

        # 1. Validate folder if provided
        if folder_id is not None:
            folder = await self.folder_repo.get_by_id(folder_id, workspace_id)
            if not folder:
                raise NotFoundException(
                    code="FOLDER_NOT_FOUND",
                    message="Target folder does not belong to this workspace.",
                )

        # 2. Build default valid ProjectDocumentV1
        initial_doc = create_default_project_document(
            aspect_ratio=aspect_ratio,
            width=width,
            height=height,
            fps=fps,
            initial_title=clean_title,
        )

        project = Project(
            workspace_id=workspace_id,
            folder_id=folder_id,
            created_by=user_id,
            title=clean_title,
            project_type=project_type,
            status="draft",
            aspect_ratio=aspect_ratio,
            width=width,
            height=height,
            fps=fps,
            duration_ms=int(initial_doc.settings.total_duration * 1000),
            revision=1,
        )

        initial_version = ProjectVersion(
            revision=1,
            document=initial_doc.model_dump(),
            created_by=user_id,
            source="initial",
        )

        return await self.repo.create_project_with_initial_version(project, initial_version)

    async def get_project(self, project_id: uuid.UUID, workspace_id: uuid.UUID) -> Project:
        """Retrieve project within workspace."""
        project = await self.repo.get_by_id(project_id, workspace_id)
        if not project:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found in this workspace.",
            )
        return project

    async def list_projects(
        self,
        workspace_id: uuid.UUID,
        folder_id: Optional[uuid.UUID] = None,
        filter_folder: bool = False,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Project]:
        """List active workspace projects with filters."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            folder_id=folder_id,
            filter_folder=filter_folder,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update_project(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: Optional[str] = None,
        folder_id: Optional[uuid.UUID] = None,
        update_folder: bool = False,
        status: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        thumbnail_asset_id: Optional[uuid.UUID] = None,
        update_thumbnail: bool = False,
    ) -> Project:
        """Update project metadata attributes with workspace validation."""
        project = await self.get_project(project_id, workspace_id)

        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise ConflictException(
                    code="PROJECT_INVALID_TITLE",
                    message="Project title cannot be empty.",
                )
            project.title = clean_title

        if update_folder:
            if folder_id is not None:
                folder = await self.folder_repo.get_by_id(folder_id, workspace_id)
                if not folder:
                    raise NotFoundException(
                        code="FOLDER_NOT_FOUND",
                        message="Target folder does not belong to this workspace.",
                    )
            project.folder_id = folder_id

        if update_thumbnail:
            if thumbnail_asset_id is not None:
                asset = await self.asset_repo.get_by_id(thumbnail_asset_id, workspace_id)
                if not asset:
                    raise NotFoundException(
                        code="ASSET_NOT_FOUND",
                        message="Thumbnail asset not found in this workspace.",
                    )
            project.thumbnail_asset_id = thumbnail_asset_id

        if status is not None:
            project.status = status

        if aspect_ratio is not None:
            project.aspect_ratio = aspect_ratio

        return await self.repo.update(project)

    async def delete_project(self, project_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        """Soft-delete project."""
        project = await self.get_project(project_id, workspace_id)
        await self.repo.soft_delete(project)

    async def create_version(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        document: ProjectDocumentV1,
        source: str = "manual",
    ) -> ProjectVersion:
        """Save a new immutable project version under optimistic concurrency control."""
        # 1. Fetch project with exclusive row lock
        project = await self.repo.get_for_update(project_id, workspace_id)
        if not project:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found in this workspace.",
            )

        # 2. Check optimistic concurrency revision match
        if project.revision != expected_revision:
            raise ConflictException(
                code="CONCURRENCY_CONFLICT",
                message=(
                    f"Revision conflict: current project revision is {project.revision}, "
                    f"but update expected revision {expected_revision}."
                ),
            )

        next_revision = project.revision + 1

        # 3. Create immutable ProjectVersion
        version = ProjectVersion(
            project_id=project.id,
            revision=next_revision,
            document=document.model_dump(),
            created_by=user_id,
            source=source,
        )
        await self.repo.create_version(version)

        # 4. Advance project revision, timestamps, and current version pointer
        project.current_version_id = version.id
        project.revision = next_revision
        project.width = document.settings.width
        project.height = document.settings.height
        project.aspect_ratio = document.settings.aspect_ratio
        project.fps = document.settings.fps
        project.duration_ms = int(document.settings.total_duration * 1000)
        await self.repo.update(project)

        return version

    async def get_version(
        self,
        version_id: uuid.UUID,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> ProjectVersion:
        """Retrieve historical version snapshot."""
        await self.get_project(project_id, workspace_id)
        version = await self.repo.get_version_by_id(version_id, project_id)
        if not version:
            raise NotFoundException(
                code="VERSION_NOT_FOUND",
                message="Project version snapshot not found.",
            )
        return version

    async def list_versions(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ProjectVersion]:
        """List version history snapshots for a project."""
        await self.get_project(project_id, workspace_id)
        return await self.repo.list_versions(project_id, limit=limit, offset=offset)

    async def get_latest_version(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[ProjectVersion]:
        """Retrieve latest version snapshot for a project."""
        versions = await self.list_versions(project_id, workspace_id, limit=1)
        return versions[0] if versions else None
