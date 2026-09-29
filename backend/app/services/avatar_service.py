"""Avatar and AvatarLook service managing identity lifecycles and asset binding."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.avatar import Avatar, AvatarLook
from app.repositories.asset import AssetRepository
from app.repositories.avatar import AvatarLookRepository, AvatarRepository
from app.schemas.avatar import CreateAvatarLookRequest, CreateAvatarRequest, UpdateAvatarLookRequest, UpdateAvatarRequest


class AvatarService:
    """Manages Workspace Avatars and their visual AvatarLooks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AvatarRepository(db)
        self.look_repo = AvatarLookRepository(db)
        self.asset_repo = AssetRepository(db)

    async def _validate_asset(self, asset_id: Optional[uuid.UUID], workspace_id: uuid.UUID, field_name: str) -> None:
        """Verify that a referenced asset exists, belongs to the workspace, and is not deleted."""
        if asset_id is not None:
            asset = await self.asset_repo.get_by_id(asset_id, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Referenced {field_name} asset '{asset_id}' does not exist or does not belong to this workspace.",
                )

    async def create_avatar(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateAvatarRequest,
    ) -> Avatar:
        """Create a new avatar with optional initial look and validated media assets."""
        # 1. Uniqueness check
        existing = await self.repo.get_by_name(workspace_id, payload.name)
        if existing:
            raise ConflictException(
                code="AVATAR_NAME_EXISTS",
                message=f"An avatar with name '{payload.name}' already exists in this workspace.",
            )

        # 2. Asset security validation
        await self._validate_asset(payload.preview_asset_id, workspace_id, "preview")
        await self._validate_asset(payload.source_asset_id, workspace_id, "source")

        avatar = Avatar(
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            avatar_type=payload.avatar_type or "custom",
            status="ready",
            visibility=payload.visibility or "workspace",
            provider=payload.provider or "mock",
            provider_reference=payload.provider_reference,
            provider_metadata=payload.provider_metadata or {},
            preview_asset_id=payload.preview_asset_id,
            source_asset_id=payload.source_asset_id,
        )
        avatar = await self.repo.create(avatar)

        # 3. Create initial look if requested
        if payload.initial_look:
            await self._validate_asset(payload.initial_look.preview_asset_id, workspace_id, "initial look preview")
            look = AvatarLook(
                avatar_id=avatar.id,
                name=payload.initial_look.name.strip(),
                description=payload.initial_look.description.strip() if payload.initial_look.description else None,
                status="ready",
                configuration=payload.initial_look.configuration or {},
                preview_asset_id=payload.initial_look.preview_asset_id,
                provider=payload.initial_look.provider or "mock",
                provider_reference=payload.initial_look.provider_reference,
            )
            await self.look_repo.create(look)

        # Reload avatar with eager loaded looks
        refreshed = await self.repo.get_by_id(avatar.id, workspace_id)
        return refreshed or avatar

    async def get_avatar(self, avatar_id: uuid.UUID, workspace_id: uuid.UUID) -> Avatar:
        """Fetch avatar strictly scoped to workspace."""
        avatar = await self.repo.get_by_id(avatar_id, workspace_id)
        if not avatar:
            raise NotFoundException(
                code="AVATAR_NOT_FOUND",
                message="Avatar not found in this workspace.",
            )
        return avatar

    async def list_avatars(
        self,
        workspace_id: uuid.UUID,
        avatar_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Avatar]:
        """List active workspace avatars."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            avatar_type=avatar_type,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update_avatar(
        self,
        avatar_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateAvatarRequest,
    ) -> Avatar:
        """Update avatar attributes with uniqueness and asset validation."""
        avatar = await self.get_avatar(avatar_id, workspace_id)

        if payload.name is not None and payload.name.strip() != avatar.name:
            existing = await self.repo.get_by_name(workspace_id, payload.name)
            if existing and existing.id != avatar.id:
                raise ConflictException(
                    code="AVATAR_NAME_EXISTS",
                    message=f"An avatar with name '{payload.name}' already exists.",
                )
            avatar.name = payload.name.strip()

        if payload.preview_asset_id is not None:
            await self._validate_asset(payload.preview_asset_id, workspace_id, "preview")
            avatar.preview_asset_id = payload.preview_asset_id

        if payload.source_asset_id is not None:
            await self._validate_asset(payload.source_asset_id, workspace_id, "source")
            avatar.source_asset_id = payload.source_asset_id

        if payload.description is not None:
            avatar.description = payload.description.strip() if payload.description else None
        if payload.avatar_type is not None:
            avatar.avatar_type = payload.avatar_type
        if payload.status is not None:
            avatar.status = payload.status
        if payload.visibility is not None:
            avatar.visibility = payload.visibility
        if payload.provider is not None:
            avatar.provider = payload.provider
        if payload.provider_reference is not None:
            avatar.provider_reference = payload.provider_reference
        if payload.provider_metadata is not None:
            avatar.provider_metadata = payload.provider_metadata

        return await self.repo.update(avatar)

    async def soft_delete_avatar(self, avatar_id: uuid.UUID, workspace_id: uuid.UUID) -> Avatar:
        """Soft-delete an avatar."""
        avatar = await self.get_avatar(avatar_id, workspace_id)
        return await self.repo.soft_delete(avatar)

    # Avatar Look methods
    async def create_look(
        self,
        avatar_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: CreateAvatarLookRequest,
    ) -> AvatarLook:
        """Add a new look to an avatar."""
        avatar = await self.get_avatar(avatar_id, workspace_id)

        existing = await self.look_repo.get_by_name(avatar.id, payload.name)
        if existing:
            raise ConflictException(
                code="AVATAR_LOOK_NAME_EXISTS",
                message=f"A look with name '{payload.name}' already exists on this avatar.",
            )

        await self._validate_asset(payload.preview_asset_id, workspace_id, "look preview")

        look = AvatarLook(
            avatar_id=avatar.id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            status="ready",
            configuration=payload.configuration or {},
            preview_asset_id=payload.preview_asset_id,
            provider=payload.provider or "mock",
            provider_reference=payload.provider_reference,
        )
        return await self.look_repo.create(look)

    async def get_look(
        self,
        avatar_id: uuid.UUID,
        look_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> AvatarLook:
        """Fetch look belonging to avatar."""
        await self.get_avatar(avatar_id, workspace_id)
        look = await self.look_repo.get_by_id(look_id, avatar_id)
        if not look:
            raise NotFoundException(
                code="AVATAR_LOOK_NOT_FOUND",
                message="Avatar look not found.",
            )
        return look

    async def list_looks(self, avatar_id: uuid.UUID, workspace_id: uuid.UUID) -> List[AvatarLook]:
        """List all looks on an avatar."""
        await self.get_avatar(avatar_id, workspace_id)
        return await self.look_repo.list_by_avatar(avatar_id)

    async def update_look(
        self,
        avatar_id: uuid.UUID,
        look_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateAvatarLookRequest,
    ) -> AvatarLook:
        """Update look configuration or attributes."""
        look = await self.get_look(avatar_id, look_id, workspace_id)

        if payload.name is not None and payload.name.strip() != look.name:
            existing = await self.look_repo.get_by_name(avatar_id, payload.name)
            if existing and existing.id != look.id:
                raise ConflictException(
                    code="AVATAR_LOOK_NAME_EXISTS",
                    message=f"A look with name '{payload.name}' already exists on this avatar.",
                )
            look.name = payload.name.strip()

        if payload.preview_asset_id is not None:
            await self._validate_asset(payload.preview_asset_id, workspace_id, "look preview")
            look.preview_asset_id = payload.preview_asset_id

        if payload.description is not None:
            look.description = payload.description.strip() if payload.description else None
        if payload.status is not None:
            look.status = payload.status
        if payload.configuration is not None:
            look.configuration = payload.configuration
        if payload.provider is not None:
            look.provider = payload.provider
        if payload.provider_reference is not None:
            look.provider_reference = payload.provider_reference

        return await self.look_repo.update(look)

    async def delete_look(
        self,
        avatar_id: uuid.UUID,
        look_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """Remove a look from an avatar."""
        look = await self.get_look(avatar_id, look_id, workspace_id)
        await self.look_repo.delete(look)
