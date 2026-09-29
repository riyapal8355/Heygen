"""BrandKit, BrandGlossary, and BrandGlossaryRule repositories for workspace-scoped brand management."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.brand import BrandGlossary, BrandGlossaryRule, BrandKit


class BrandKitRepository:
    """Data access operations for Brand Kits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        brand_kit_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[BrandKit]:
        """Fetch brand kit strictly scoped to workspace."""
        query = select(BrandKit).where(
            BrandKit.id == brand_kit_id,
            BrandKit.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(BrandKit.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[BrandKit]:
        """Fetch brand kit by name within workspace (case-insensitive)."""
        query = select(BrandKit).where(
            BrandKit.workspace_id == workspace_id,
            func.lower(BrandKit.name) == func.lower(name.strip()),
        )
        if not include_deleted:
            query = query.where(BrandKit.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_default(self, workspace_id: uuid.UUID) -> Optional[BrandKit]:
        """Fetch workspace's active default brand kit."""
        query = select(BrandKit).where(
            BrandKit.workspace_id == workspace_id,
            BrandKit.is_default.is_(True),
            BrandKit.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def clear_default(self, workspace_id: uuid.UUID) -> None:
        """Unset is_default flag on all existing kits in workspace."""
        stmt = (
            update(BrandKit)
            .where(
                BrandKit.workspace_id == workspace_id,
                BrandKit.is_default.is_(True),
            )
            .values(is_default=False)
        )
        await self.db.execute(stmt)

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BrandKit]:
        """List active brand kits in a workspace."""
        query = (
            select(BrandKit)
            .where(
                BrandKit.workspace_id == workspace_id,
                BrandKit.deleted_at.is_(None),
            )
            .order_by(BrandKit.is_default.desc(), BrandKit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, brand_kit: BrandKit) -> BrandKit:
        """Persist a new brand kit."""
        self.db.add(brand_kit)
        await self.db.flush()
        return brand_kit

    async def update(self, brand_kit: BrandKit) -> BrandKit:
        """Mark brand kit updated."""
        brand_kit.updated_at = datetime.now(timezone.utc)
        self.db.add(brand_kit)
        await self.db.flush()
        return brand_kit

    async def soft_delete(self, brand_kit: BrandKit) -> BrandKit:
        """Soft-delete brand kit record."""
        brand_kit.deleted_at = datetime.now(timezone.utc)
        self.db.add(brand_kit)
        await self.db.flush()
        return brand_kit


class BrandGlossaryRepository:
    """Data access operations for Brand Glossaries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        glossary_id: uuid.UUID,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[BrandGlossary]:
        """Fetch glossary strictly scoped to workspace, eagerly loading its rules."""
        query = (
            select(BrandGlossary)
            .options(selectinload(BrandGlossary.rules))
            .where(
                BrandGlossary.id == glossary_id,
                BrandGlossary.workspace_id == workspace_id,
            )
        )
        if not include_deleted:
            query = query.where(BrandGlossary.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_name(
        self,
        workspace_id: uuid.UUID,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[BrandGlossary]:
        """Fetch glossary by name within workspace (case-insensitive)."""
        query = select(BrandGlossary).where(
            BrandGlossary.workspace_id == workspace_id,
            func.lower(BrandGlossary.name) == func.lower(name.strip()),
        )
        if not include_deleted:
            query = query.where(BrandGlossary.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        brand_kit_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BrandGlossary]:
        """List active glossaries in a workspace with optional brand kit filter."""
        query = (
            select(BrandGlossary)
            .options(selectinload(BrandGlossary.rules))
            .where(
                BrandGlossary.workspace_id == workspace_id,
                BrandGlossary.deleted_at.is_(None),
            )
        )
        if brand_kit_id:
            query = query.where(BrandGlossary.brand_kit_id == brand_kit_id)

        query = query.order_by(BrandGlossary.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, glossary: BrandGlossary) -> BrandGlossary:
        """Persist a new glossary."""
        self.db.add(glossary)
        await self.db.flush()
        return glossary

    async def update(self, glossary: BrandGlossary) -> BrandGlossary:
        """Mark glossary updated."""
        glossary.updated_at = datetime.now(timezone.utc)
        self.db.add(glossary)
        await self.db.flush()
        return glossary

    async def soft_delete(self, glossary: BrandGlossary) -> BrandGlossary:
        """Soft-delete glossary record."""
        glossary.deleted_at = datetime.now(timezone.utc)
        self.db.add(glossary)
        await self.db.flush()
        return glossary


class BrandGlossaryRuleRepository:
    """Data access operations for Brand Glossary Rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        rule_id: uuid.UUID,
        glossary_id: Optional[uuid.UUID] = None,
    ) -> Optional[BrandGlossaryRule]:
        """Fetch rule by ID, optionally scoped to parent glossary."""
        query = (
            select(BrandGlossaryRule)
            .options(selectinload(BrandGlossaryRule.glossary))
            .where(BrandGlossaryRule.id == rule_id)
        )
        if glossary_id is not None:
            query = query.where(BrandGlossaryRule.glossary_id == glossary_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_glossary(self, glossary_id: uuid.UUID) -> List[BrandGlossaryRule]:
        """List all terminology rules in a glossary."""
        query = (
            select(BrandGlossaryRule)
            .where(BrandGlossaryRule.glossary_id == glossary_id)
            .order_by(BrandGlossaryRule.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, rule: BrandGlossaryRule) -> BrandGlossaryRule:
        """Persist a new glossary rule."""
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def update(self, rule: BrandGlossaryRule) -> BrandGlossaryRule:
        """Update rule."""
        rule.updated_at = datetime.now(timezone.utc)
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def delete(self, rule: BrandGlossaryRule) -> None:
        """Delete rule."""
        await self.db.delete(rule)
        await self.db.flush()
