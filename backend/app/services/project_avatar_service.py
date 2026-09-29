"""Project-level avatar video synthesis and lip-sync orchestration service.

Coordinates:
1. Avatar reference asset retrieval from MinIO
2. Speech audio asset retrieval from MinIO
3. Neural lip-sync execution (Wav2Lip-ONNX CPU / Mock)
4. Video asset ingestion and thumbnail creation
5. Safe ProjectDocumentV1 update (scene.avatar.video_asset_id)
6. Optimistic Concurrency Control (OCC) immutable version creation
"""

import copy
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Union

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import LipSyncContractRequest, MediaAssetRef
from app.ai.registry import get_avatar_provider
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.models.avatar import Avatar
from app.models.project import ProjectVersion
from app.schemas.project_document import DocumentAssetRef, ProjectDocumentV1
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.avatar_service import AvatarService
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)


class ProjectAvatarOrchestrator:
    """Coordinates avatar lip-sync video generation and timeline integration."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.avatar_service = AvatarService(db)
        self.asset_manager = AssetLifecycleManager(db)

    async def generate_project_avatar_video(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        scene_id: Optional[str] = None,
        avatar_id_override: Optional[Union[uuid.UUID, str]] = None,
        provider_override: Optional[str] = None,
        device_override: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Tuple[ProjectVersion, Dict[str, Any]]:
        """Generate talking-avatar video for a scene and update ProjectDocumentV1 under OCC."""
        # 1. Fetch project with workspace isolation
        project = await self.project_service.get_project(project_id, workspace_id)

        # Early OCC revision check to prevent wasted AI inference
        if project.revision != expected_revision:
            raise ConflictException(
                code="CONCURRENCY_CONFLICT",
                message=(
                    f"Revision conflict: current project revision is {project.revision}, "
                    f"but update expected revision {expected_revision}."
                ),
            )

        if not project.current_version_id:
            raise NotFoundException(
                code="PROJECT_VERSION_NOT_FOUND",
                message="Project has no active version snapshot.",
            )

        current_version = await self.project_service.get_version(
            project.current_version_id, project_id, workspace_id
        )

        # 2. Strict immutability: deep-copy the document
        doc_dict = copy.deepcopy(current_version.document)
        doc = ProjectDocumentV1.model_validate(doc_dict)

        # 3. Locate target scene
        target_scene = None
        if scene_id:
            target_scene = next((s for s in doc.scenes if s.id == scene_id), None)
            if not target_scene:
                raise NotFoundException(
                    code="SCENE_NOT_FOUND",
                    message=f"Scene with ID '{scene_id}' not found in project document.",
                )
        else:
            # Pick first scene configured with both avatar and speech
            for s in doc.scenes:
                if s.avatar and s.speech and s.speech.audio_asset_id:
                    target_scene = s
                    break
            if not target_scene:
                # Pick any scene with avatar
                for s in doc.scenes:
                    if s.avatar:
                        target_scene = s
                        break

        if not target_scene:
            raise NotFoundException(
                code="SCENE_NOT_CONFIGURED",
                message="No eligible scene with avatar configuration found in project.",
            )

        if not target_scene.avatar:
            raise NotFoundException(
                code="AVATAR_NOT_CONFIGURED",
                message="Selected scene has no avatar actor configured.",
            )

        if not target_scene.speech or not target_scene.speech.audio_asset_id:
            raise NotFoundException(
                code="SPEECH_AUDIO_NOT_FOUND",
                message="Selected scene has no speech audio asset. Synthesize speech audio first.",
            )

        # 4. Resolve Avatar with strict workspace RBAC authorization
        target_avatar_id_str = str(avatar_id_override) if avatar_id_override else target_scene.avatar.avatar_id
        target_avatar_uuid: Optional[uuid.UUID] = None
        try:
            target_avatar_uuid = uuid.UUID(target_avatar_id_str)
        except ValueError:
            target_avatar_uuid = None

        avatar_record: Optional[Avatar] = None
        if target_avatar_uuid:
            # Global query to distinguish nonexistent/deleted from cross-workspace permission denial
            q = select(Avatar).where(Avatar.id == target_avatar_uuid, Avatar.deleted_at.is_(None))
            res = await self.db.execute(q)
            avatar_record = res.scalars().first()
            if not avatar_record:
                raise NotFoundException(
                    code="AVATAR_NOT_FOUND",
                    message=f"Avatar with ID '{target_avatar_uuid}' not found.",
                )
            if avatar_record.visibility != "public" and avatar_record.workspace_id != workspace_id:
                raise ForbiddenException(
                    code="AVATAR_ACCESS_DENIED",
                    message=f"Access denied: avatar '{avatar_record.name}' belongs to another workspace.",
                )
        else:
            q = select(Avatar).where(
                or_(
                    func.lower(Avatar.name) == func.lower(target_avatar_id_str.strip()),
                    Avatar.provider_reference == target_avatar_id_str.strip(),
                ),
                Avatar.deleted_at.is_(None),
            )
            res = await self.db.execute(q)
            matches = res.scalars().all()
            if not matches:
                raise NotFoundException(
                    code="AVATAR_NOT_FOUND",
                    message=f"Avatar '{target_avatar_id_str}' not found.",
                )
            accessible = [a for a in matches if a.visibility == "public" or a.workspace_id == workspace_id]
            if not accessible:
                raise ForbiddenException(
                    code="AVATAR_ACCESS_DENIED",
                    message=f"Access denied: avatar '{matches[0].name}' belongs to another workspace.",
                )
            avatar_record = accessible[0]
            target_avatar_uuid = avatar_record.id

        if avatar_record.status != "ready":
            raise ConflictException(
                code="AVATAR_UNAVAILABLE",
                message=f"Avatar '{avatar_record.name}' is currently not ready (status: {avatar_record.status}).",
            )

        source_image_asset_id = avatar_record.source_asset_id or avatar_record.preview_asset_id
        if not source_image_asset_id:
            raise NotFoundException(
                code="AVATAR_IMAGE_ASSET_MISSING",
                message=f"Avatar '{avatar_record.name}' has no reference source or preview image asset.",
            )

        source_image_asset = await self.asset_manager.asset_repo.get_by_id(source_image_asset_id, workspace_id)
        if not source_image_asset:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message=f"Avatar reference image asset '{source_image_asset_id}' not found.",
            )

        # 5. Resolve Speech Audio Asset
        try:
            speech_audio_uuid = uuid.UUID(target_scene.speech.audio_asset_id)
        except ValueError:
            raise ValidationException(
                code="INVALID_AUDIO_ASSET_ID",
                message=f"Speech audio asset ID '{target_scene.speech.audio_asset_id}' is not a valid UUID.",
            )

        speech_audio_asset = await self.asset_manager.asset_repo.get_by_id(speech_audio_uuid, workspace_id)
        if not speech_audio_asset:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message=f"Scene speech audio asset '{speech_audio_uuid}' not found in workspace.",
            )

        # 6. Retrieve media payloads from MinIO storage
        storage = get_storage_provider()
        try:
            avatar_image_bytes = await storage.get_object(source_image_asset.storage_key)
        except Exception as e:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message=f"Failed to retrieve avatar image asset '{source_image_asset.id}' from storage: {str(e)}",
            )

        try:
            speech_audio_bytes = await storage.get_object(speech_audio_asset.storage_key)
        except Exception as e:
            raise NotFoundException(
                code="ASSET_NOT_FOUND",
                message=f"Failed to retrieve speech audio asset '{speech_audio_asset.id}' from storage: {str(e)}",
            )

        # Cooperative cancellation check before starting inference
        if cancellation_checker and await cancellation_checker():
            raise AIProviderException(code="INFERENCE_CANCELLED", message="Lip-sync was cancelled.")

        # 7. Dynamic provider resolution: avatar -> avatar provider -> provider implementation
        raw_provider_name = (
            provider_override.strip().lower()
            if provider_override
            else (avatar_record.provider.strip().lower() if avatar_record.provider else None)
        )
        if not raw_provider_name or raw_provider_name in ("legacy_delaunay", "delaunay"):
            resolved_provider_name = "gpu_avatar"
        else:
            resolved_provider_name = raw_provider_name

        settings = get_settings()
        is_real_mode = (settings.AI_PROVIDER_MODE == "real")

        if is_real_mode and resolved_provider_name == "mock" and provider_override != "mock":
            raise ConflictException(
                code="AVATAR_UNAVAILABLE",
                message=f"Avatar '{avatar_record.name}' uses mock provider which is unavailable for real neural video synthesis.",
            )

        avatar_provider = get_avatar_provider(name=resolved_provider_name, device=device_override)
        provider_name = getattr(avatar_provider, "provider_name", resolved_provider_name or "avatar")

        if is_real_mode and provider_name == "mock" and provider_override != "mock":
            raise AIRuntimeUnavailableException(
                message="Real AI mode is active (AI_PROVIDER_MODE='real'); silent fallback to mock avatar is strictly forbidden.",
                code="REAL_MODE_MOCK_FALLBACK_FORBIDDEN",
            )

        # Truthful GPU requirement health check
        is_healthy, health_reason = avatar_provider.health_check()
        if not is_healthy:
            is_gpu_req = "GPU_REQUIRED" in health_reason or "CUDA" in health_reason
            raise AIRuntimeUnavailableException(
                code="GPU_REQUIRED" if is_gpu_req else "AVATAR_UNAVAILABLE",
                message=f"Neural avatar provider unavailable on this machine: {health_reason}",
                details={
                    "provider_status": "GPU_REQUIRED" if is_gpu_req else "UNAVAILABLE",
                    "code": "GPU_REQUIRED" if is_gpu_req else "AVATAR_UNAVAILABLE",
                },
            )

        fps = 25

        if progress_callback:
            await progress_callback(25, "running_lip_sync_inference")

        avatar_opts = {
            "avatar_name": avatar_record.provider_reference or "annie",
            "workspace_id": str(workspace_id),
        }

        if hasattr(avatar_provider, "generate_talking_video"):
            mp4_bytes, duration_seconds, frame_count = await avatar_provider.generate_talking_video(
                avatar_image_bytes=avatar_image_bytes,
                audio_bytes=speech_audio_bytes,
                fps=fps,
                options=avatar_opts,
                progress_callback=progress_callback,
                cancellation_checker=cancellation_checker,
            )
        elif hasattr(avatar_provider, "synthesize_avatar_video"):
            mp4_bytes, duration_seconds, frame_count = await avatar_provider.synthesize_avatar_video(
                avatar_image_bytes=avatar_image_bytes,
                audio_bytes=speech_audio_bytes,
                fps=fps,
                options=avatar_opts,
                progress_callback=progress_callback,
                cancellation_checker=cancellation_checker,
            )
        else:
            # Use strongly typed contract for other providers (e.g. MockAvatarProvider)
            req = LipSyncContractRequest(
                workspace_id=workspace_id,
                avatar_look_asset=MediaAssetRef(
                    asset_id=source_image_asset.id,
                    storage_key=source_image_asset.storage_key,
                ),
                audio_asset=MediaAssetRef(
                    asset_id=speech_audio_asset.id,
                    storage_key=speech_audio_asset.storage_key,
                ),
                output_format="mp4",
                resolution="1080p",
                fps=fps,
            )
            result = await avatar_provider.lip_sync(req)
            mp4_bytes = await storage.get_object(result.output_storage_key)
            duration_seconds = result.duration_seconds
            frame_count = result.frame_count

        if cancellation_checker and await cancellation_checker():
            raise AIProviderException(code="INFERENCE_CANCELLED", message="Lip-sync was cancelled.")

        # 8. Ingest synthesized video into MinIO as workspace Asset
        if progress_callback:
            await progress_callback(85, "ingesting_video_asset")

        avatar_video_asset = await self.asset_manager.ingest_generated_asset(
            workspace_id=workspace_id,
            created_by=user_id,
            content=mp4_bytes,
            original_filename=f"avatar_{target_avatar_uuid.hex[:8]}_lipsync.mp4",
            asset_type="video",
            mime_type="video/mp4",
            metadata={
                "avatar_id": str(target_avatar_uuid),
                "audio_asset_id": str(speech_audio_uuid),
                "duration_seconds": duration_seconds,
                "frame_count": frame_count,
                "fps": fps,
                "provider": provider_name,
            },
        )

        # 9. Update SceneAvatar safely with video_asset_id and canonical avatar_id
        target_scene.avatar.video_asset_id = str(avatar_video_asset.id)
        target_scene.avatar.avatar_id = str(target_avatar_uuid)

        # Append to doc.assets manifest if not present
        if not any(a.asset_id == str(avatar_video_asset.id) for a in doc.assets):
            doc.assets.append(
                DocumentAssetRef(
                    asset_id=str(avatar_video_asset.id),
                    asset_type="video",
                    storage_key=avatar_video_asset.storage_key,
                )
            )

        # 10. Commit new immutable ProjectVersion under optimistic concurrency
        new_version = await self.project_service.create_version(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=expected_revision,
            document=doc,
            source="avatar_video",
        )

        logger.info(
            "Synthesized avatar video for project %s scene %s: asset %s, revision %d -> %d",
            project_id,
            target_scene.id,
            avatar_video_asset.id,
            expected_revision,
            new_version.revision,
        )

        metrics = {
            "video_asset_id": str(avatar_video_asset.id),
            "storage_key": avatar_video_asset.storage_key,
            "duration_seconds": duration_seconds,
            "frame_count": frame_count,
            "fps": fps,
            "provider": provider_name,
            "scene_id": target_scene.id,
        }
        return new_version, metrics

    async def orchestrate_avatar_video(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        scene_id: Optional[str] = None,
        avatar_id_override: Optional[Union[uuid.UUID, str]] = None,
        provider: Optional[str] = None,
        device: Optional[str] = None,
        provider_override: Optional[str] = None,
        device_override: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> ProjectVersion:
        """Alias for Celery background tasks returning committed ProjectVersion."""
        resolved_provider = provider or provider_override
        resolved_device = device or device_override
        new_version, _ = await self.generate_project_avatar_video(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=expected_revision,
            scene_id=scene_id,
            avatar_id_override=avatar_id_override,
            provider_override=resolved_provider,
            device_override=resolved_device,
            progress_callback=progress_callback,
            cancellation_checker=cancellation_checker,
        )
        return new_version


