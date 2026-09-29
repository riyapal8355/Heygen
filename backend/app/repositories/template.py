"""Template and TemplateVersion repository for workspace-scoped starter documents."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.template import Template, TemplateVersion


class TemplateRepository:
    """Data access operations for Workspace Templates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Template]:
        """Fetch template strictly scoped to workspace or public, eagerly loading active version."""
        query = (
            select(Template)
            .options(selectinload(Template.current_version))
            .where(
                Template.id == template_id,
                or_(
                    Template.workspace_id == workspace_id,
                    Template.visibility.in_(["public", "global"]),
                ),
            )
        )
        if not include_deleted:
            query = query.where(Template.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[Template]:
        """Fetch template by name within workspace (case-insensitive)."""
        query = select(Template).where(
            Template.workspace_id == workspace_id,
            func.lower(Template.name) == func.lower(name.strip()),
        )
        if not include_deleted:
            query = query.where(Template.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Template]:
        """List active templates in a workspace or public with optional filters."""
        query = (
            select(Template)
            .options(selectinload(Template.current_version))
            .where(
                or_(
                    Template.workspace_id == workspace_id,
                    Template.visibility.in_(["public", "global"]),
                ),
                Template.deleted_at.is_(None),
            )
        )
        if category:
            query = query.where(Template.category == category)
        if status:
            query = query.where(Template.status == status)
        if search:
            query = query.where(Template.name.ilike(f"%{search.strip()}%"))

        query = query.order_by(Template.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, template: Template) -> Template:
        """Persist a new template."""
        self.db.add(template)
        await self.db.flush()
        return template

    async def update(self, template: Template) -> Template:
        """Mark template updated."""
        template.updated_at = datetime.now(timezone.utc)
        self.db.add(template)
        await self.db.flush()
        return template

    async def soft_delete(self, template: Template) -> Template:
        """Soft-delete template record."""
        template.deleted_at = datetime.now(timezone.utc)
        self.db.add(template)
        await self.db.flush()
        return template


class TemplateVersionRepository:
    """Data access operations for immutable Template Versions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        version_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> Optional[TemplateVersion]:
        """Fetch version snapshot belonging to a specific template."""
        query = select(TemplateVersion).where(
            TemplateVersion.id == version_id,
            TemplateVersion.template_id == template_id,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_revision(
        self,
        template_id: uuid.UUID,
        revision: int,
    ) -> Optional[TemplateVersion]:
        """Fetch specific immutable revision of a template."""
        query = select(TemplateVersion).where(
            TemplateVersion.template_id == template_id,
            TemplateVersion.revision == revision,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_template(self, template_id: uuid.UUID) -> List[TemplateVersion]:
        """List all version snapshots of a template."""
        query = (
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.revision.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, version: TemplateVersion) -> TemplateVersion:
        """Persist a new immutable version snapshot."""
        self.db.add(version)
        await self.db.flush()
        return version
