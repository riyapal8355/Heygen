"""Project Audio Transcription Orchestrator service.

Coordinates speech-to-text recognition across scene narration and audio tracks,
maps structured subtitle segments into ProjectDocumentV1,
and commits new immutable versions under atomic optimistic concurrency control (OCC).
"""

import copy
import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import TranscriptionResult
from app.ai.registry import AIProviderRegistry, get_ai_registry
from app.core.exceptions import ConflictException, NotFoundException
from app.models.project import ProjectVersion
from app.schemas.project_document import ProjectDocumentV1
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider


class ProjectTranscriptionOrchestrator:
    """Orchestrates audio transcription, subtitle cue alignment, and timeline synchronization."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
        asset_manager: Optional[AssetLifecycleManager] = None,
    ) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.ai_registry = ai_registry or get_ai_registry()
        self.asset_manager = asset_manager or AssetLifecycleManager(db)

    async def transcribe_project_audio(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        scene_id: Optional[str] = None,
        audio_asset_id: Optional[uuid.UUID] = None,
        language: Optional[str] = None,
        provider_override: Optional[str] = None,
    ) -> Tuple[ProjectVersion, TranscriptionResult]:
        """Transcribe project speech audio and atomically update timeline with subtitle cues."""
        # 1. Fetch project and active version snapshot
        project = await self.project_service.get_project(project_id, workspace_id)
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

        # 3. Locate target audio asset or storage key
        target_storage_key: Optional[str] = None
        target_scene = None

        if scene_id:
            target_scene = next((s for s in doc.scenes if s.id == scene_id), None)
            if not target_scene:
                raise NotFoundException(
                    code="SCENE_NOT_FOUND",
                    message=f"Scene with ID '{scene_id}' not found in project document.",
                )

        if audio_asset_id:
            asset = await self.asset_manager.asset_repo.get_by_id(audio_asset_id, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Audio asset with ID '{audio_asset_id}' not found in workspace.",
                )
            target_storage_key = asset.storage_key
        elif target_scene and target_scene.speech and target_scene.speech.audio_asset_id:
            asset_uuid = uuid.UUID(target_scene.speech.audio_asset_id)
            asset = await self.asset_manager.asset_repo.get_by_id(asset_uuid, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Scene audio asset with ID '{asset_uuid}' not found.",
                )
            target_storage_key = asset.storage_key
        else:
            # Fallback: scan scenes for any existing speech audio asset
            for s in doc.scenes:
                if s.speech and s.speech.audio_asset_id:
                    target_scene = s
                    asset_uuid = uuid.UUID(s.speech.audio_asset_id)
                    asset = await self.asset_manager.asset_repo.get_by_id(asset_uuid, workspace_id)
                    if asset:
                        target_storage_key = asset.storage_key
                        break

        if not target_storage_key:
            raise NotFoundException(
                code="ASR_AUDIO_NOT_FOUND",
                message="No audio asset available for transcription in specified scene or project.",
            )

        # 4. Resolve ASR provider and execute neural speech recognition
        asr_provider = self.ai_registry.get_asr_provider(provider_override)

        # If provider supports transcribe_bytes, fetch bytes directly from MinIO
        storage = get_storage_provider()
        audio_bytes = storage.get_object_bytes(target_storage_key)

        if hasattr(asr_provider, "transcribe_bytes"):
            transcription = await asr_provider.transcribe_bytes(
                audio_bytes=audio_bytes,
                language=language,
                include_word_timestamps=True,
            )
        else:
            transcription = await asr_provider.transcribe_audio(
                audio_storage_key=target_storage_key,
                language=language,
            )

        # 5. Safely attach subtitle cues to scene without breaking SceneLayer compositor semantics
        if target_scene:
            target_scene.subtitles = transcription.segments
            if target_scene.speech and (not target_scene.speech.script or not target_scene.speech.script.strip()):
                target_scene.speech.script = transcription.full_text

        # Record project-level transcript metadata
        doc.metadata["transcription"] = {
            "detected_language": transcription.detected_language,
            "duration_seconds": transcription.duration_seconds,
            "confidence": transcription.confidence,
            "segment_count": len(transcription.segments),
            "full_text": transcription.full_text,
            "audio_storage_key": target_storage_key,
        }

        # 6. Atomic optimistic concurrency commit via ProjectService
        new_version = await self.project_service.create_version(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=expected_revision,
            document=doc,
            source="asr_transcription",
        )

        return new_version, transcription
