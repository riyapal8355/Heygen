"""Brand business service managing brand identities, design kits, and terminology glossaries."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.brand import BrandGlossary, BrandGlossaryRule, BrandKit
from app.repositories.asset import AssetRepository
from app.repositories.brand import BrandGlossaryRepository, BrandGlossaryRuleRepository, BrandKitRepository
from app.schemas.brand import (
    CreateBrandGlossaryRequest,
    CreateBrandGlossaryRuleRequest,
    CreateBrandKitRequest,
    UpdateBrandGlossaryRequest,
    UpdateBrandGlossaryRuleRequest,
    UpdateBrandKitRequest,
)


class BrandService:
    """Manages Workspace BrandKits, Glossaries, and GlossaryRules."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kit_repo = BrandKitRepository(db)
        self.glossary_repo = BrandGlossaryRepository(db)
        self.rule_repo = BrandGlossaryRuleRepository(db)
        self.asset_repo = AssetRepository(db)

    async def _validate_asset(self, asset_id: Optional[uuid.UUID], workspace_id: uuid.UUID) -> None:
        """Verify brand logo asset belongs to the workspace and is active."""
        if asset_id is not None:
            asset = await self.asset_repo.get_by_id(asset_id, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Referenced logo asset '{asset_id}' does not exist or does not belong to this workspace.",
                )

    # BrandKit Operations
    async def create_brand_kit(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateBrandKitRequest,
    ) -> BrandKit:
        """Create a new brand kit."""
        clean_name = payload.name.strip()
        existing = await self.kit_repo.get_by_name(workspace_id, clean_name)
        if existing:
            raise ConflictException(
                code="BRAND_KIT_NAME_EXISTS",
                message=f"A brand kit with name '{clean_name}' already exists in this workspace.",
            )

        await self._validate_asset(payload.logo_asset_id, workspace_id)

        # If this is marked default, clear any prior default
        if payload.is_default:
            await self.kit_repo.clear_default(workspace_id)

        brand_kit = BrandKit(
            workspace_id=workspace_id,
            created_by=user_id,
            name=clean_name,
            description=payload.description.strip() if payload.description else None,
            logo_asset_id=payload.logo_asset_id,
            colors=payload.colors or {},
            typography=payload.typography or {},
            settings=payload.settings or {},
            is_default=payload.is_default or False,
        )
        return await self.kit_repo.create(brand_kit)

    async def get_brand_kit(self, brand_kit_id: uuid.UUID, workspace_id: uuid.UUID) -> BrandKit:
        """Fetch brand kit strictly scoped to workspace."""
        kit = await self.kit_repo.get_by_id(brand_kit_id, workspace_id)
        if not kit:
            raise NotFoundException(
                code="BRAND_KIT_NOT_FOUND",
                message="Brand kit not found in this workspace.",
            )
        return kit

    async def list_brand_kits(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BrandKit]:
        """List active brand kits in workspace."""
        return await self.kit_repo.list_by_workspace(workspace_id, limit=limit, offset=offset)

    async def update_brand_kit(
        self,
        brand_kit_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateBrandKitRequest,
    ) -> BrandKit:
        """Update brand kit parameters."""
        kit = await self.get_brand_kit(brand_kit_id, workspace_id)

        if payload.name is not None and payload.name.strip() != kit.name:
            clean_name = payload.name.strip()
            existing = await self.kit_repo.get_by_name(workspace_id, clean_name)
            if existing and existing.id != kit.id:
                raise ConflictException(
                    code="BRAND_KIT_NAME_EXISTS",
                    message=f"A brand kit with name '{clean_name}' already exists.",
                )
            kit.name = clean_name

        if payload.logo_asset_id is not None:
            await self._validate_asset(payload.logo_asset_id, workspace_id)
            kit.logo_asset_id = payload.logo_asset_id

        if payload.is_default is True and not kit.is_default:
            await self.kit_repo.clear_default(workspace_id)
            kit.is_default = True
        elif payload.is_default is False:
            kit.is_default = False

        if payload.description is not None:
            kit.description = payload.description.strip() if payload.description else None
        if payload.colors is not None:
            kit.colors = payload.colors
        if payload.typography is not None:
            kit.typography = payload.typography
        if payload.settings is not None:
            kit.settings = payload.settings

        return await self.kit_repo.update(kit)

    async def soft_delete_brand_kit(self, brand_kit_id: uuid.UUID, workspace_id: uuid.UUID) -> BrandKit:
        """Soft-delete brand kit."""
        kit = await self.get_brand_kit(brand_kit_id, workspace_id)
        return await self.kit_repo.soft_delete(kit)

    # BrandGlossary Operations
    async def create_glossary(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateBrandGlossaryRequest,
    ) -> BrandGlossary:
        """Create a new terminology glossary."""
        clean_name = payload.name.strip()
        existing = await self.glossary_repo.get_by_name(workspace_id, clean_name)
        if existing:
            raise ConflictException(
                code="BRAND_GLOSSARY_NAME_EXISTS",
                message=f"A glossary with name '{clean_name}' already exists in this workspace.",
            )

        if payload.brand_kit_id is not None:
            await self.get_brand_kit(payload.brand_kit_id, workspace_id)

        glossary = BrandGlossary(
            workspace_id=workspace_id,
            brand_kit_id=payload.brand_kit_id,
            created_by=user_id,
            name=clean_name,
            description=payload.description.strip() if payload.description else None,
            status=payload.status or "active",
        )
        return await self.glossary_repo.create(glossary)

    async def get_glossary(self, glossary_id: uuid.UUID, workspace_id: uuid.UUID) -> BrandGlossary:
        """Fetch glossary strictly scoped to workspace."""
        glossary = await self.glossary_repo.get_by_id(glossary_id, workspace_id)
        if not glossary:
            raise NotFoundException(
                code="BRAND_GLOSSARY_NOT_FOUND",
                message="Brand glossary not found in this workspace.",
            )
        return glossary

    async def list_glossaries(
        self,
        workspace_id: uuid.UUID,
        brand_kit_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BrandGlossary]:
        """List active glossaries in workspace."""
        return await self.glossary_repo.list_by_workspace(
            workspace_id=workspace_id,
            brand_kit_id=brand_kit_id,
            limit=limit,
            offset=offset,
        )

    async def update_glossary(
        self,
        glossary_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateBrandGlossaryRequest,
    ) -> BrandGlossary:
        """Update glossary attributes."""
        glossary = await self.get_glossary(glossary_id, workspace_id)

        if payload.name is not None and payload.name.strip() != glossary.name:
            clean_name = payload.name.strip()
            existing = await self.glossary_repo.get_by_name(workspace_id, clean_name)
            if existing and existing.id != glossary.id:
                raise ConflictException(
                    code="BRAND_GLOSSARY_NAME_EXISTS",
                    message=f"A glossary with name '{clean_name}' already exists.",
                )
            glossary.name = clean_name

        if payload.brand_kit_id is not None:
            await self.get_brand_kit(payload.brand_kit_id, workspace_id)
            glossary.brand_kit_id = payload.brand_kit_id

        if payload.description is not None:
            glossary.description = payload.description.strip() if payload.description else None
        if payload.status is not None:
            glossary.status = payload.status

        return await self.glossary_repo.update(glossary)

    async def soft_delete_glossary(self, glossary_id: uuid.UUID, workspace_id: uuid.UUID) -> BrandGlossary:
        """Soft-delete glossary."""
        glossary = await self.get_glossary(glossary_id, workspace_id)
        return await self.glossary_repo.soft_delete(glossary)

    # BrandGlossaryRule Operations
    async def create_rule(
        self,
        glossary_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: CreateBrandGlossaryRuleRequest,
    ) -> BrandGlossaryRule:
        """Add a terminology rule to a glossary."""
        glossary = await self.get_glossary(glossary_id, workspace_id)

        rule = BrandGlossaryRule(
            glossary_id=glossary.id,
            source_term=payload.source_term.strip(),
            preferred_term=payload.preferred_term.strip(),
            forbidden_term=payload.forbidden_term.strip() if payload.forbidden_term else None,
            source_language=payload.source_language or "en",
            target_language=payload.target_language,
            case_sensitive=payload.case_sensitive or False,
            status=payload.status or "active",
        )
        return await self.rule_repo.create(rule)

    async def get_rule(
        self,
        rule_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> BrandGlossaryRule:
        """Fetch rule ensuring parent glossary belongs to caller's workspace."""
        rule = await self.rule_repo.get_by_id(rule_id)
        if not rule or not rule.glossary or rule.glossary.workspace_id != workspace_id or rule.glossary.deleted_at is not None:
            raise NotFoundException(
                code="BRAND_GLOSSARY_RULE_NOT_FOUND",
                message="Brand glossary rule not found in this workspace.",
            )
        return rule

    async def list_rules(
        self,
        glossary_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> List[BrandGlossaryRule]:
        """List all terminology rules in a glossary."""
        glossary = await self.get_glossary(glossary_id, workspace_id)
        return await self.rule_repo.list_by_glossary(glossary.id)

    async def update_rule(
        self,
        rule_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateBrandGlossaryRuleRequest,
    ) -> BrandGlossaryRule:
        """Update a terminology rule."""
        rule = await self.get_rule(rule_id, workspace_id)

        if payload.source_term is not None:
            rule.source_term = payload.source_term.strip()
        if payload.preferred_term is not None:
            rule.preferred_term = payload.preferred_term.strip()
        if payload.forbidden_term is not None:
            rule.forbidden_term = payload.forbidden_term.strip() if payload.forbidden_term else None
        if payload.source_language is not None:
            rule.source_language = payload.source_language
        if payload.target_language is not None:
            rule.target_language = payload.target_language
        if payload.case_sensitive is not None:
            rule.case_sensitive = payload.case_sensitive
        if payload.status is not None:
            rule.status = payload.status

        return await self.rule_repo.update(rule)

    async def delete_rule(
        self,
        rule_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """Delete a terminology rule."""
        rule = await self.get_rule(rule_id, workspace_id)
        await self.rule_repo.delete(rule)
