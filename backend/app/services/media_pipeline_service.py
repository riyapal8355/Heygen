"""Media Generation Pipeline domain service.

Orchestrates the complete real end-to-end media generation pipeline:
Prompt -> Script -> TTS Voice Audio -> Avatar Visual / Lip Sync -> FFmpeg Composition -> Captions -> Real MP4 -> MinIO Storage -> Asset -> ProjectVersion -> Completed Job.
"""

import asyncio
import copy
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.registry import get_talking_avatar_provider
from app.core.config import get_settings
from app.core.exceptions import AIRuntimeUnavailableException
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.media.compositor import TimelineCompositor
from app.media.ffprobe import FFprobeService
from app.media.workspace import MediaWorkspace
from app.models.avatar import Avatar
from app.models.job import Job
from app.models.project import Project, ProjectVersion
from app.repositories.asset import AssetRepository
from app.repositories.avatar import AvatarRepository
from app.repositories.project import ProjectRepository
from app.schemas.project_document import (
    DocumentAssetRef,
    ProjectDocumentV1,
    Scene,
    SceneAvatar,
    SceneSpeech,
)
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.job_service import JobService
from app.services.project_service import ProjectService
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)


class MediaPipelineService:
    """Orchestrates multi-stage media generation, real audio synthesis, avatar rendering, and FFmpeg compositing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.job_service = JobService(db)
        self.project_service = ProjectService(db)
        self.asset_manager = AssetLifecycleManager(db)
        self.compositor = TimelineCompositor()
        self.ffprobe = FFprobeService()

    async def execute_generation_pipeline(
        self,
        job_id: uuid.UUID,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the real media generation pipeline for a project generation job."""
        job = await self.job_service.job_repo.get_by_id(job_id)
        if not job:
            logger.error("Job %s not found for media generation pipeline", job_id)
            return {"status": "not_found"}

        if job.status == "cancelled":
            return {"status": "cancelled"}

        payload = job.payload or {}
        project_id_str = payload.get("project_id")
        if not project_id_str:
            err_msg = "Missing required project_id in job payload"
            await self.job_service.mark_failed(job_id, {"error": err_msg}, err_msg)
            return {"status": "failed", "error": err_msg}

        project_id = uuid.UUID(project_id_str)
        workspace_id = job.workspace_id
        user_id = job.created_by

        try:
            # -------------------------------------------------------------
            # Stage 1: Preparing
            # -------------------------------------------------------------
            await self.job_service.mark_started(
                job_id=job_id,
                stage="preparing",
                message="Preparing project timeline and assets",
                celery_task_id=task_id or str(uuid.uuid4()),
            )

            project = await self.project_service.get_project(project_id, workspace_id)
            if not project or not project.current_version_id:
                raise ValueError(f"Project {project_id} has no valid active version")

            current_version = await self.project_service.get_version(
                project.current_version_id, project_id, workspace_id
            )
            doc = ProjectDocumentV1.model_validate(copy.deepcopy(current_version.document))

            # -------------------------------------------------------------
            # Stage 2: Generating Audio (TTS)
            # -------------------------------------------------------------
            await self.job_service.update_progress(
                job_id=job_id,
                progress_percent=20,
                stage="generating_audio",
                message="Synthesizing narration audio with neural TTS",
                details={"scene_count": len(doc.scenes)},
            )

            speech_orchestrator = ProjectSpeechOrchestrator(self.db)
            scenes_to_synth = [
                s.id for s in doc.scenes
                if s.speech and s.speech.script and s.speech.script.strip()
            ]

            if scenes_to_synth:
                speech_version = await speech_orchestrator.synthesize_project_speech(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    expected_revision=project.revision,
                    scene_ids=scenes_to_synth,
                    voice_id_override=payload.get("voice_id"),
                )
                await self.db.commit()
                await self.db.refresh(project)
                doc = ProjectDocumentV1.model_validate(copy.deepcopy(speech_version.document))

            # Populate timed subtitles from speech scripts if not already present
            for sc in doc.scenes:
                if sc.speech and sc.speech.script and not sc.subtitles:
                    words = sc.speech.script.strip().split()
                    if words:
                        cue_size = 5
                        cue_chunks = [" ".join(words[i : i + cue_size]) for i in range(0, len(words), cue_size)]
                        cue_dur = sc.duration / max(1, len(cue_chunks))
                        sc.subtitles = [
                            {
                                "id": c_idx + 1,
                                "start": round(c_idx * cue_dur, 2),
                                "end": round(min(sc.duration, (c_idx + 1) * cue_dur), 2),
                                "text": c_text,
                                "enabled": True,
                            }
                            for c_idx, c_text in enumerate(cue_chunks)
                        ]

            # -------------------------------------------------------------
            # Stage 3: Real Talking Presenter Video / Neural Lip-Sync
            # -------------------------------------------------------------
            has_avatar_scene = any(s.avatar for s in doc.scenes)
            is_explicit_static = (
                payload.get("avatar_mode") == "static"
                or payload.get("enable_lipsync") is False
            )
            pipeline_mode = "static_avatar" if is_explicit_static else "neural_avatar"

            if has_avatar_scene and not is_explicit_static:
                await self.job_service.update_progress(
                    job_id=job_id,
                    progress_percent=45,
                    stage="synthesizing_avatar_lipsync",
                    message="Synthesizing speech-synchronized talking presenter video",
                    details={"scenes_count": len(doc.scenes)},
                )

                talking_provider = get_talking_avatar_provider(
                    name=payload.get("avatar_provider") or payload.get("provider"),
                    device=payload.get("device"),
                )
                is_healthy, health_reason = talking_provider.health_check()
                if not is_healthy:
                    is_gpu_req = "GPU_REQUIRED" in health_reason or "CUDA" in health_reason
                    raise AIRuntimeUnavailableException(
                        code="GPU_REQUIRED" if is_gpu_req else "TALKING_AVATAR_UNAVAILABLE",
                        message=f"Neural talking-avatar rendering is unavailable on this machine: {health_reason}",
                        details={
                            "provider_status": "GPU_REQUIRED" if is_gpu_req else "UNAVAILABLE",
                            "code": "GPU_REQUIRED" if is_gpu_req else "TALKING_AVATAR_UNAVAILABLE",
                        },
                    )

                storage = get_storage_provider()
                asset_repo = AssetRepository(self.db)
                av_scenes = [s for s in doc.scenes if s.avatar and s.speech and s.speech.audio_asset_id]
                total_av = max(1, len(av_scenes))

                for a_idx, scene in enumerate(av_scenes):
                    pct = 45 + int(12 * ((a_idx + 1) / total_av))
                    await self.job_service.update_progress(
                        job_id=job_id,
                        progress_percent=pct,
                        stage="synthesizing_avatar_lipsync",
                        message=f"Synthesizing presenter lip-sync for scene {scene.sequence or a_idx + 1}/{total_av}",
                    )

                    # Resolve avatar image asset
                    av_id = scene.avatar.avatar_id
                    av_asset = None
                    try:
                        av_uuid = uuid.UUID(str(av_id))
                        from sqlalchemy import select
                        stmt = select(Avatar).where(Avatar.id == av_uuid)
                        a_res = await self.db.execute(stmt)
                        db_av = a_res.scalars().first()
                        if db_av and (db_av.preview_asset_id or db_av.source_asset_id):
                            ref_id = db_av.preview_asset_id or db_av.source_asset_id
                            av_asset = await asset_repo.get_by_id(ref_id, workspace_id)
                    except Exception:
                        pass

                    if not av_asset:
                        try:
                            av_asset = await asset_repo.get_by_id(uuid.UUID(str(av_id)), workspace_id)
                        except Exception:
                            pass

                    if not av_asset:
                        raise ValueError(f"Avatar reference image asset for avatar '{av_id}' not found in workspace.")

                    audio_asset = await asset_repo.get_by_id(uuid.UUID(scene.speech.audio_asset_id), workspace_id)
                    if not audio_asset:
                        raise ValueError(f"Scene speech audio asset '{scene.speech.audio_asset_id}' not found in workspace.")

                    img_bytes = storage.get_object_bytes(av_asset.storage_key)
                    aud_bytes = storage.get_object_bytes(audio_asset.storage_key)

                    talking_opts = {"idle_motion": True, "blinking": True}
                    if db_av and db_av.provider_reference:
                        talking_opts["avatar_name"] = db_av.provider_reference

                    vid_bytes, av_dur, total_frames = await talking_provider.generate_talking_video(
                        avatar_image_bytes=img_bytes,
                        audio_bytes=aud_bytes,
                        fps=25,
                        options=talking_opts,
                    )

                    talking_av_asset = await self.asset_manager.ingest_generated_asset(
                        workspace_id=workspace_id,
                        created_by=user_id,
                        content=vid_bytes,
                        original_filename=f"talking_avatar_{scene.id}.mp4",
                        asset_type="video",
                        mime_type="video/mp4",
                        metadata={
                            "scene_id": scene.id,
                            "avatar_id": str(av_id),
                            "duration_seconds": av_dur,
                            "frame_count": total_frames,
                            "generated": True,
                        },
                    )
                    scene.avatar.video_asset_id = str(talking_av_asset.id)
                    doc.assets.append(
                        DocumentAssetRef(
                            asset_id=str(talking_av_asset.id),
                            asset_type="video",
                            storage_key=talking_av_asset.storage_key,
                        )
                    )
            elif has_avatar_scene:
                await self.job_service.update_progress(
                    job_id=job_id,
                    progress_percent=55,
                    stage="preparing_avatar",
                    message="Preparing static avatar visual plate (user requested fallback)",
                )

            # -------------------------------------------------------------
            # Stage 4: Rendering (FFmpeg Compositor)
            # -------------------------------------------------------------
            await self.job_service.update_progress(
                job_id=job_id,
                progress_percent=60,
                stage="rendering",
                message="Compositing scenes, audio, and captions with FFmpeg",
                details={"total_duration": doc.settings.total_duration},
            )

            async with MediaWorkspace(prefix=f"gen_{job.id}_") as mws:
                async def _progress_cb(pct: int, stage_name: str, details: Optional[Dict[str, Any]] = None) -> None:
                    # Scale render progress between 60% and 90%
                    scaled_pct = 60 + int((pct / 100.0) * 30)
                    await self.job_service.update_progress(
                        job_id=job_id,
                        progress_percent=scaled_pct,
                        stage="rendering",
                        message=f"Rendering: {stage_name}",
                        details=details or {},
                    )

                render_result = await self.compositor.render_project(
                    document=doc,
                    workspace_id=workspace_id,
                    db=self.db,
                    media_workspace=mws,
                    progress_callback=_progress_cb,
                )

                # Preserve intermediate scene clips in test-results/visual_quality for inspection
                vq_dir = Path("test-results/visual_quality")
                if vq_dir.exists():
                    try:
                        import shutil
                        for sc_idx, sc_clip in enumerate(getattr(render_result, "scene_clips", [])):
                            if sc_clip and Path(sc_clip).exists():
                                shutil.copy2(sc_clip, vq_dir / f"scene_{sc_idx + 1}.mp4")
                        if render_result.video_path and Path(render_result.video_path).exists():
                            shutil.copy2(render_result.video_path, vq_dir / "final.mp4")
                    except Exception as copy_err:
                        logger.warning("Could not copy intermediate scene clips to visual_quality: %s", copy_err)

                # Validate rendered output MP4 via FFprobe
                probe = await self.ffprobe.validate_render_output(
                    render_result.video_path,
                    min_duration=0.1,
                    require_video=True,
                    require_audio=bool(scenes_to_synth),
                )

                # ---------------------------------------------------------
                # Stage 5: Uploading
                # ---------------------------------------------------------
                await self.job_service.update_progress(
                    job_id=job_id,
                    progress_percent=92,
                    stage="uploading",
                    message="Ingesting rendered video and thumbnail into storage",
                )

                video_asset = await self.asset_manager.ingest_generated_asset(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    content=render_result.video_path,
                    original_filename=f"render_{project_id}.mp4",
                    asset_type="video",
                    mime_type="video/mp4",
                    metadata={
                        "job_id": str(job_id),
                        "project_id": str(project_id),
                        "duration_seconds": probe.duration_seconds,
                        "resolution": f"{render_result.canvas_profile.width}x{render_result.canvas_profile.height}",
                        "fps": render_result.canvas_profile.fps,
                        "codec": probe.codec_name,
                        "generated": True,
                    },
                )

                thumb_asset = await self.asset_manager.ingest_generated_asset(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    content=render_result.thumbnail_path,
                    original_filename=f"thumbnail_{project_id}.png",
                    asset_type="image",
                    mime_type="image/png",
                    metadata={"job_id": str(job_id), "project_id": str(project_id), "generated": True},
                )

                # Update target Project status, thumbnail pointer, and duration
                project.thumbnail_asset_id = thumb_asset.id
                project.status = "ready"
                project.duration_ms = int(probe.duration_seconds * 1000)
                await self.project_service.repo.update(project)

                # Append video asset to document assets list and commit updated version
                doc.assets.append(
                    DocumentAssetRef(
                        asset_id=str(video_asset.id),
                        asset_type="video",
                        storage_key=video_asset.storage_key,
                    )
                )
                final_version = await self.project_service.create_version(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    expected_revision=project.revision,
                    document=doc,
                    source="video_generation",
                )
                await self.db.commit()

                # ---------------------------------------------------------
                # Stage 6: Completed
                # ---------------------------------------------------------
                storage = get_storage_provider()
                video_url = storage.generate_download_url(video_asset.storage_key, expires_in_seconds=86400)
                thumb_url = storage.generate_download_url(thumb_asset.storage_key, expires_in_seconds=86400)

                curr_start = 0.0
                scenes_meta = []
                for s in doc.scenes:
                    dur = float(s.duration or 5.0)
                    bg_asset_id = s.background.get("asset_id") if isinstance(s.background, dict) else None
                    scenes_meta.append({
                        "id": s.id,
                        "sequence": s.sequence,
                        "start": round(curr_start, 2),
                        "end": round(curr_start + dur, 2),
                        "duration": dur,
                        "avatarId": s.avatar.avatar_id if s.avatar else None,
                        "avatarVideoAssetId": s.avatar.video_asset_id if s.avatar else None,
                        "voiceId": s.speech.voice_id if s.speech else None,
                        "background": s.background.model_dump() if s.background else None,
                        "backgroundAssetId": bg_asset_id,
                        "cameraMotion": getattr(s, "camera_motion", "static") or "static",
                        "transition": s.transition.model_dump() if s.transition else {"type": "cut", "duration": 0.0},
                        "captions": s.subtitles or [],
                        "layers": [l.model_dump() for l in s.layers] if s.layers else [],
                    })
                    curr_start += dur

                result = {
                    "project_id": str(project.id),
                    "projectId": str(project.id),
                    "project_version_id": str(final_version.id),
                    "projectVersionId": str(final_version.id),
                    "revision": final_version.revision,
                    "output_asset_id": str(video_asset.id),
                    "output_storage_key": video_asset.storage_key,
                    "video_url": video_url,
                    "videoUrl": video_url,
                    "download_url": video_url,
                    "thumbnail_asset_id": str(thumb_asset.id),
                    "thumbnail_storage_key": thumb_asset.storage_key,
                    "thumbnail_url": thumb_url,
                    "duration": probe.duration_seconds,
                    "duration_seconds": probe.duration_seconds,
                    "resolution": f"{render_result.canvas_profile.width}x{render_result.canvas_profile.height}",
                    "fps": render_result.canvas_profile.fps,
                    "format": "mp4",
                    "codec": probe.codec_name,
                    "size_bytes": video_asset.size_bytes,
                    "pipeline_mode": pipeline_mode,
                    "scenes": scenes_meta,
                    "status": "completed",
                }

                await self.job_service.mark_succeeded(
                    job_id=job_id,
                    result=result,
                    message="Video generation completed successfully",
                )
                return result

        except Exception as exc:
            logger.error("Media generation pipeline failed for job %s: %s", job_id, exc, exc_info=True)
            try:
                await self.db.rollback()
            except Exception:
                pass

            try:
                project = await self.project_service.get_project(project_id, workspace_id)
                if project:
                    is_gpu_req = "GPU_REQUIRED" in str(exc) or getattr(exc, "code", "") == "GPU_REQUIRED"
                    project.status = "draft"
                    latest_version = await self.project_service.get_latest_version(project.id, workspace_id)
                    if latest_version and latest_version.document:
                        from sqlalchemy.orm.attributes import flag_modified
                        doc_dict = dict(latest_version.document)
                        meta = dict(doc_dict.get("metadata") or {})
                        meta["generation_status"] = "failed"
                        meta["generation_error"] = "GPU_REQUIRED" if is_gpu_req else str(exc)
                        meta["generation_incomplete"] = True
                        meta["render_status"] = "incomplete"
                        doc_dict["metadata"] = meta
                        latest_version.document = doc_dict
                        flag_modified(latest_version, "document")
                        await self.project_service.repo.update_version(latest_version)
                    await self.project_service.repo.update(project)
                    await self.db.commit()
            except Exception as pe:
                logger.warning("Could not mark project as incomplete draft on failure: %s", pe)

            try:
                error_details = {"error": str(exc), "type": type(exc).__name__}
                if hasattr(exc, "details") and isinstance(exc.details, dict):
                    error_details.update(exc.details)
                if hasattr(exc, "code") and exc.code:
                    error_details["code"] = exc.code
                if "GPU_REQUIRED" in str(exc) or getattr(exc, "code", "") == "GPU_REQUIRED":
                    error_details["provider_status"] = "GPU_REQUIRED"
                    error_details["code"] = "GPU_REQUIRED"

                await self.job_service.mark_failed(
                    job_id=job_id,
                    error_details=error_details,
                    message=f"Video generation failed: {str(exc)}",
                )
            except Exception as mark_err:
                logger.error("Could not mark job %s as failed: %s", job_id, mark_err)
            return {"status": "failed", "error": str(exc), "error_details": error_details}


async def run_pipeline_in_background(job_id: uuid.UUID) -> None:
    """Entry point for async background task execution."""
    try:
        async with async_session_factory() as session:
            service = MediaPipelineService(session)
            await service.execute_generation_pipeline(job_id)
    except Exception as exc:
        logger.error("Background media pipeline execution error for job %s: %s", job_id, exc)
