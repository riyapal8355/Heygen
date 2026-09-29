"""Voice business service managing speech synthesis voices and presets."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    RateLimitedException,
    ValidationException,
)
from app.core.redis import check_rate_limit
from app.models.voice import Voice
from app.repositories.asset import AssetRepository
from app.repositories.voice import VoiceRepository
from app.schemas.job import JobSubmitRequest
from app.schemas.voice import CreateVoiceRequest, UpdateVoiceRequest
from app.schemas.voice_clone import VoiceCloneJobResponse, VoiceCloneRequest
from app.services.job_service import JobService


class VoiceService:
    """Manages Workspace Voices and cloning metadata."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VoiceRepository(db)
        self.asset_repo = AssetRepository(db)

    async def _validate_asset(self, asset_id: Optional[uuid.UUID], workspace_id: uuid.UUID) -> None:
        """Verify that preview audio asset exists and belongs to the workspace."""
        if asset_id is not None:
            asset = await self.asset_repo.get_by_id(asset_id, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Referenced preview audio asset '{asset_id}' does not exist or does not belong to this workspace.",
                )

    async def create_voice(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateVoiceRequest,
    ) -> Voice:
        """Create a new voice with asset validation and uniqueness checks."""
        existing = await self.repo.get_by_name(workspace_id, payload.name)
        if existing:
            raise ConflictException(
                code="VOICE_NAME_EXISTS",
                message=f"A voice with name '{payload.name}' already exists in this workspace.",
            )

        await self._validate_asset(payload.preview_asset_id, workspace_id)

        voice = Voice(
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            voice_type=payload.voice_type or "custom",
            language=payload.language or "en",
            gender=payload.gender or "neutral",
            provider=payload.provider or "mock",
            provider_reference=payload.provider_reference,
            provider_metadata=payload.provider_metadata or {},
            preview_asset_id=payload.preview_asset_id,
            status="ready",
            visibility=payload.visibility or "workspace",
        )
        return await self.repo.create(voice)

    async def get_voice(self, voice_id: uuid.UUID, workspace_id: uuid.UUID) -> Voice:
        """Fetch voice strictly scoped to workspace."""
        voice = await self.repo.get_by_id(voice_id, workspace_id)
        if not voice:
            raise NotFoundException(
                code="VOICE_NOT_FOUND",
                message="Voice not found in this workspace.",
            )
        return voice

    async def list_voices(
        self,
        workspace_id: uuid.UUID,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        voice_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Voice]:
        """List active workspace voices with filtering."""
        return await self.repo.list_by_workspace(
            workspace_id=workspace_id,
            language=language,
            gender=gender,
            voice_type=voice_type,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update_voice(
        self,
        voice_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: UpdateVoiceRequest,
    ) -> Voice:
        """Update voice metadata."""
        voice = await self.get_voice(voice_id, workspace_id)

        if payload.name is not None and payload.name.strip() != voice.name:
            existing = await self.repo.get_by_name(workspace_id, payload.name)
            if existing and existing.id != voice.id:
                raise ConflictException(
                    code="VOICE_NAME_EXISTS",
                    message=f"A voice with name '{payload.name}' already exists.",
                )
            voice.name = payload.name.strip()

        if payload.preview_asset_id is not None:
            await self._validate_asset(payload.preview_asset_id, workspace_id)
            voice.preview_asset_id = payload.preview_asset_id

        if payload.description is not None:
            voice.description = payload.description.strip() if payload.description else None
        if payload.voice_type is not None:
            voice.voice_type = payload.voice_type
        if payload.language is not None:
            voice.language = payload.language
        if payload.gender is not None:
            voice.gender = payload.gender
        if payload.provider is not None:
            voice.provider = payload.provider
        if payload.provider_reference is not None:
            voice.provider_reference = payload.provider_reference
        if payload.provider_metadata is not None:
            voice.provider_metadata = payload.provider_metadata
        if payload.status is not None:
            voice.status = payload.status
        if payload.visibility is not None:
            voice.visibility = payload.visibility

        return await self.repo.update(voice)

    async def soft_delete_voice(self, voice_id: uuid.UUID, workspace_id: uuid.UUID) -> Voice:
        """Soft-delete voice."""
        voice = await self.get_voice(voice_id, workspace_id)
        return await self.repo.soft_delete(voice)

    async def clone_voice_intent(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: VoiceCloneRequest,
    ) -> VoiceCloneJobResponse:
        """Register voice clone intent, validate reference audio asset, and queue Celery job."""
        # 1. Enforce Redis rate limiting for voice cloning (CPU-heavy task)
        rate_key = f"rate_limit:voice_clone:{workspace_id}:{user_id}"
        allowed = await check_rate_limit(rate_key, max_requests=5, window_seconds=60)
        if not allowed:
            raise RateLimitedException(
                code="RATE_LIMIT_EXCEEDED",
                message="Voice cloning rate limit exceeded (maximum 5 requests per minute). Please try again shortly.",
            )

        # 2. Uniqueness check within workspace
        existing = await self.repo.get_by_name(workspace_id, payload.name)
        if existing:
            raise ConflictException(
                code="VOICE_NAME_EXISTS",
                message=f"A voice with name '{payload.name}' already exists in this workspace.",
            )

        # 3. Source audio asset validation (must exist in workspace and be audio)
        asset = await self.asset_repo.get_by_id(payload.reference_asset_id, workspace_id)
        if not asset:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message=f"Referenced audio asset '{payload.reference_asset_id}' does not exist or does not belong to this workspace.",
            )
        if asset.asset_type != "audio" and not (asset.mime_type and asset.mime_type.startswith("audio/")):
            raise ValidationException(
                code="INVALID_ASSET_TYPE",
                message=f"Referenced asset '{payload.reference_asset_id}' must be an audio asset (got type '{asset.asset_type}', mime '{asset.mime_type}').",
            )

        # 4. Pre-allocate Voice entity in pending status
        # Secure representation path scoped to workspace: workspaces/{workspace_id}/voices/{voice_id}/embedding.pt
        voice_id = uuid.uuid4()
        embedding_storage_key = f"workspaces/{workspace_id}/voices/{voice_id}/embedding.pt"
        voice = Voice(
            id=voice_id,
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            voice_type="cloned",
            language=payload.language or "en",
            gender=payload.gender or "neutral",
            provider="openvoice",
            provider_reference=embedding_storage_key,
            provider_metadata={
                "source_asset_id": str(payload.reference_asset_id),
                "model": "openvoice_v2",
                "provider": "openvoice",
                "language": payload.language or "en",
                "status": "pending",
                "embedding_storage_key": embedding_storage_key,
            },
            status="pending",
            visibility="workspace",
        )
        await self.repo.create(voice)

        # 5. Submit Celery AI job
        job_service = JobService(self.db)
        job_request = JobSubmitRequest(
            job_type="voice_clone",
            priority=1,
            payload={
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "voice_id": str(voice.id),
                "voice_name": voice.name,
                "reference_asset_id": str(payload.reference_asset_id),
                "language": voice.language,
                "gender": voice.gender,
                "embedding_storage_key": embedding_storage_key,
            },
        )
        job, _ = await job_service.submit_job(
            workspace_id=workspace_id,
            user_id=user_id,
            request=job_request,
        )

        return VoiceCloneJobResponse(
            job_id=job.id,
            voice_id=voice.id,
            status=job.status,
            voice_name=voice.name,
            workspace_id=workspace_id,
            created_at=job.created_at,
        )

