"""Template business service managing reusable starter projects and immutable version snapshots."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.template import Template, TemplateVersion
from app.repositories.asset import AssetRepository
from app.repositories.template import TemplateRepository, TemplateVersionRepository
from app.schemas.project_document import create_default_project_document
from app.schemas.template import CreateTemplateRequest, CreateTemplateVersionRequest, UpdateTemplateRequest


class TemplateService:
    """Manages Workspace Templates and their immutable version snapshots."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRepository(db)
        self.version_repo = TemplateVersionRepository(db)
        self.asset_repo = AssetRepository(db)

    async def _validate_asset(self, asset_id: Optional[uuid.UUID], workspace_id: uuid.UUID) -> None:
        """Verify thumbnail asset belongs to current workspace and is active."""
        if asset_id is not None:
            asset = await self.asset_repo.get_by_id(asset_id, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Referenced thumbnail asset '{asset_id}' does not exist or does not belong to this workspace.",
                )

    async def create_template(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateTemplateRequest,
    ) -> Template:
        """Create a new template and initialize with revision 1 immutable TemplateVersion."""
        clean_name = payload.name.strip()
        existing = await self.repo.get_by_name(workspace_id, clean_name)
        if existing:
            raise ConflictException(
                code="TEMPLATE_NAME_EXISTS",
                message=f"A template with name '{clean_name}' already exists in this workspace.",
            )

        await self._validate_asset(payload.thumbnail_asset_id, workspace_id)

        # Build initial document snapshot
        if payload.initial_document:
            document_dict = payload.initial_document
        else:
            default_doc = create_default_project_document(
                initial_title=clean_name,
                aspect_ratio="16:9",
            )
            document_dict = default_doc.model_dump()

        template = Template(
            workspace_id=workspace_id,
            created_by=user_id,
            name=clean_name,
            description=payload.description.strip() if payload.description else None,
            category=payload.category or "marketing",
            status="active",
            visibility=payload.visibility or "workspace",
            thumbnail_asset_id=payload.thumbnail_asset_id,
            configuration=payload.configuration or {},
            revision=1,
        )
        template = await self.repo.create(template)

        initial_version = TemplateVersion(
            template_id=template.id,
            revision=1,
            document=document_dict,
            created_by=user_id,
        )
        initial_version = await self.version_repo.create(initial_version)

        template.current_version_id = initial_version.id
        await self.repo.update(template)

        refreshed = await self.repo.get_by_id(template.id, workspace_id)
        return refreshed or template

    async def get_template(self, template_id: uuid.UUID, workspace_id: uuid.UUID) -> Template:
        """Fetch template strictly scoped to workspace."""
        template = await self.repo.get_by_id(template_id, workspace_id)
        if not template:
            raise NotFoundException(
                code="TEMPLATE_NOT_FOUND",
                message="Template not found in this workspace.",
            )
        return template

    async def list_templates(
        self,
        workspace_id: uuid.UUID,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Template]:
        """List active templates in a workspace."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            category=category,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update_template(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateTemplateRequest,
    ) -> Template:
        """Update template metadata. Note: TemplateVersions are immutable and unchanged by this operation."""
        template = await self.get_template(template_id, workspace_id)

        if payload.name is not None and payload.name.strip() != template.name:
            clean_name = payload.name.strip()
            existing = await self.repo.get_by_name(workspace_id, clean_name)
            if existing and existing.id != template.id:
                raise ConflictException(
                    code="TEMPLATE_NAME_EXISTS",
                    message=f"A template with name '{clean_name}' already exists.",
                )
            template.name = clean_name

        if payload.thumbnail_asset_id is not None:
            await self._validate_asset(payload.thumbnail_asset_id, workspace_id)
            template.thumbnail_asset_id = payload.thumbnail_asset_id

        if payload.description is not None:
            template.description = payload.description.strip() if payload.description else None
        if payload.category is not None:
            template.category = payload.category
        if payload.status is not None:
            template.status = payload.status
        if payload.visibility is not None:
            template.visibility = payload.visibility
        if payload.configuration is not None:
            template.configuration = payload.configuration

        return await self.repo.update(template)

    async def soft_delete_template(self, template_id: uuid.UUID, workspace_id: uuid.UUID) -> Template:
        """Soft-delete a template."""
        template = await self.get_template(template_id, workspace_id)
        return await self.repo.soft_delete(template)

    # Immutable TemplateVersion methods
    async def create_version(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateTemplateVersionRequest,
    ) -> TemplateVersion:
        """Create a new immutable version snapshot and increment the template revision."""
        template = await self.get_template(template_id, workspace_id)

        new_revision = template.revision + 1
        new_version = TemplateVersion(
            template_id=template.id,
            revision=new_revision,
            document=payload.document,
            created_by=user_id,
        )
        new_version = await self.version_repo.create(new_version)

        template.revision = new_revision
        template.current_version_id = new_version.id
        await self.repo.update(template)

        return new_version

    async def get_version(
        self,
        template_id: uuid.UUID,
        version_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> TemplateVersion:
        """Fetch specific immutable version snapshot."""
        await self.get_template(template_id, workspace_id)
        version = await self.version_repo.get_by_id(version_id, template_id)
        if not version:
            raise NotFoundException(
                code="TEMPLATE_VERSION_NOT_FOUND",
                message="Template version snapshot not found.",
            )
        return version

    async def list_versions(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> List[TemplateVersion]:
        """List all version snapshots for a template."""
        await self.get_template(template_id, workspace_id)
        return await self.version_repo.list_by_template(template_id)

    async def instantiate_template(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
    ):
        """Instantiate template into a new Project and revision 1 ProjectVersion."""
        template = await self.get_template(template_id, workspace_id)
        template_version = getattr(template, "current_version", None)
        if not template_version and template.current_version_id:
            template_version = await self.version_repo.get_by_id(template.current_version_id, template.id)
        if not template_version or not template_version.document:
            raise NotFoundException(
                code="TEMPLATE_DOCUMENT_NOT_FOUND",
                message="Template version document not found.",
            )

        doc = template_version.document
        settings = doc.get("settings", {})
        aspect_ratio = settings.get("aspect_ratio", "16:9")
        width = settings.get("width", 1920)
        height = settings.get("height", 1080)
        fps = settings.get("fps", 30)
        total_duration = settings.get("total_duration", 5.0)

        project_title = (title or f"{template.name} Project").strip()

        from app.models.project import Project, ProjectVersion
        from app.repositories.project import ProjectRepository

        project = Project(
            workspace_id=workspace_id,
            folder_id=None,
            created_by=user_id,
            title=project_title,
            project_type="standard",
            status="draft",
            aspect_ratio=aspect_ratio,
            width=width,
            height=height,
            fps=fps,
            duration_ms=int(total_duration * 1000),
            revision=1,
        )

        initial_version = ProjectVersion(
            revision=1,
            document=doc,
            created_by=user_id,
            source="template_instantiate",
        )

        project_repo = ProjectRepository(self.db)
        created_project = await project_repo.create_project_with_initial_version(project, initial_version)
        return created_project
