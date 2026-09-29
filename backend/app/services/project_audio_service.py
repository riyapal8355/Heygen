"""Project Audio Enhancement & Studio Speech Cleanup Orchestrator service.

Coordinates neural noise suppression, silence trimming, and broadcast mastering
across scene speech assets in a project, ingests enhanced audio assets to MinIO,
updates scene timeline durations, and commits new immutable versions under OCC.
"""

import copy
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import AudioEnhanceContractRequest, AudioEnhanceContractResult
from app.ai.interfaces import AudioEnhanceResult
from app.ai.registry import AIProviderRegistry, get_ai_registry
from app.core.config import get_settings
from app.core.exceptions import ConflictException, NotFoundException
from app.media.ffmpeg import FFmpegService
from app.media.temp_manager import MediaTempManager
from app.models.project import ProjectVersion
from app.schemas.project_document import ProjectDocumentV1
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider


class ProjectAudioOrchestrator:
    """Orchestrates neural audio enhancement, studio speech cleanup, and timeline synchronization."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
        ffmpeg_service: Optional[FFmpegService] = None,
        asset_manager: Optional[AssetLifecycleManager] = None,
    ) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.ai_registry = ai_registry or get_ai_registry()
        self.ffmpeg_service = ffmpeg_service or FFmpegService()
        self.asset_manager = asset_manager or AssetLifecycleManager(db)

    async def enhance_project_speech(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        scene_id: Optional[str] = None,
        denoise: bool = True,
        remove_silence: bool = False,
        remove_fillers: bool = False,
        master_audio: bool = True,
        provider_override: Optional[str] = None,
    ) -> Tuple[ProjectVersion, Dict[str, Any]]:
        """Enhance speech audio in target scenes and atomically commit new project version."""
        # 1. Fetch project and enforce optimistic concurrency control
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

        # 3. Locate target scene(s) with audio assets
        target_scenes = []
        if scene_id:
            scene = next((s for s in doc.scenes if s.id == scene_id), None)
            if not scene:
                raise NotFoundException(
                    code="SCENE_NOT_FOUND",
                    message=f"Scene with ID '{scene_id}' not found in project document.",
                )
            if not scene.speech or not scene.speech.audio_asset_id:
                raise NotFoundException(
                    code="AUDIO_ASSET_NOT_FOUND",
                    message=f"Scene '{scene_id}' has no speech audio asset to enhance.",
                )
            target_scenes.append(scene)
        else:
            for s in doc.scenes:
                if s.speech and s.speech.audio_asset_id:
                    target_scenes.append(s)

        if not target_scenes:
            raise NotFoundException(
                code="NO_AUDIO_TO_ENHANCE",
                message="No scenes with valid speech audio assets found in project document.",
            )

        # 4. Resolve audio enhancement provider
        provider = self.ai_registry.get_audio_enhance_provider(provider_override)
        storage = get_storage_provider()
        settings = get_settings()
        is_mock_mode = (settings.AI_PROVIDER_MODE == "mock")

        enhanced_scenes_summary = []
        for target_scene in target_scenes:
            asset_uuid = uuid.UUID(target_scene.speech.audio_asset_id)
            asset = await self.asset_manager.asset_repo.get_by_id(asset_uuid, workspace_id)
            if not asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message=f"Speech audio asset '{asset_uuid}' for scene '{target_scene.id}' not found in workspace.",
                )

            # Retrieve source audio bytes from storage
            raw_audio_bytes = storage.get_object_bytes(asset.storage_key)

            # Execute enhancement
            result: AudioEnhanceResult = await provider.enhance_audio(
                audio_bytes=raw_audio_bytes,
                denoise=denoise,
                remove_silence=remove_silence,
                remove_fillers=remove_fillers,
                master_audio=master_audio,
            )

            # Measure actual duration via FFmpeg probe
            duration_seconds = result.duration_seconds
            with MediaTempManager(prefix=f"enhanced_{target_scene.id}_") as tmp_dir:
                tmp_wav = tmp_dir / f"enhanced_{target_scene.id}.wav"
                tmp_wav.write_bytes(result.audio_bytes)

                probe = await self.ffmpeg_service.probe(
                    tmp_wav,
                    allow_mock_fallback=is_mock_mode,
                )
                if probe.duration_seconds > 0:
                    duration_seconds = probe.duration_seconds

            # Ingest enhanced audio asset
            new_asset = await self.asset_manager.ingest_generated_asset(
                workspace_id=workspace_id,
                created_by=user_id,
                content=result.audio_bytes,
                original_filename=f"enhanced_speech_{target_scene.id}.wav",
                asset_type="audio",
                mime_type="audio/wav",
                metadata={
                    "project_id": str(project_id),
                    "scene_id": target_scene.id,
                    "source_asset_id": str(asset.id),
                    "duration_seconds": duration_seconds,
                    "noise_reduction_db": result.noise_reduction_db,
                    "silence_trimmed_seconds": result.silence_trimmed_seconds,
                    "fillers_removed": result.fillers_removed,
                    "fillers_status": result.fillers_status,
                    "mastered": result.mastered,
                    "sample_rate": result.sample_rate,
                    "enhanced": True,
                },
            )

            # Update scene speech audio reference
            target_scene.speech.audio_asset_id = str(new_asset.id)
            if remove_silence and duration_seconds > 0:
                target_scene.duration = round(duration_seconds + 0.5, 2)

            enhanced_scenes_summary.append({
                "scene_id": target_scene.id,
                "original_asset_id": str(asset.id),
                "enhanced_asset_id": str(new_asset.id),
                "duration_seconds": duration_seconds,
                "silence_trimmed_seconds": result.silence_trimmed_seconds,
                "fillers_status": result.fillers_status,
                "metrics": result.metrics,
            })

        # Recalculate total project duration
        doc.settings.total_duration = round(sum(s.duration for s in doc.scenes), 2)

        # 5. Atomic optimistic concurrency commit
        new_version = await self.project_service.create_version(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=expected_revision,
            document=doc,
            source="audio_enhancement",
        )

        enhancement_metadata = {
            "project_id": str(project_id),
            "version_id": str(new_version.id),
            "revision": new_version.revision,
            "scenes_enhanced": len(enhanced_scenes_summary),
            "details": enhanced_scenes_summary,
        }

        return new_version, enhancement_metadata
