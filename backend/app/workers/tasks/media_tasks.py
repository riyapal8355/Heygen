"""Media processing and video rendering worker tasks (Queue: cpu_media)."""

import uuid
from typing import Any, Dict, Optional
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.job_service import JobService
from app.workers.base import HeyZenBaseTask, run_async
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _execute_render_video(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    """Execute multi-stage video rendering pipeline using MediaWorkspace, TimelineCompositor, and AssetLifecycleManager."""
    from app.services.asset_lifecycle import AssetLifecycleManager

    async with async_session_factory() as db:
        job_service = JobService(db)
        job = await job_service.job_repo.get_by_id(job_id)
        if not job:
            logger.error("Job %s not found for video rendering", job_id)
            return {"status": "not_found"}

        if job.status == "cancelled":
            logger.info("Job %s was cancelled before execution started", job_id)
            return {"status": "cancelled"}

        payload = job.payload or {}
        project_id_str = payload.get("project_id")

        try:
            # Stage 1: Started
            await job_service.mark_started(
                job_id=job_id,
                stage="analyzing_timeline",
                message="Analyzing project timeline and track hierarchy",
                celery_task_id=task_id,
            )

            # Check cooperative cancellation
            current_job = await job_service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            settings = get_settings()

            if settings.AI_PROVIDER_MODE != "mock":
                # =========================================================================
                # REAL MEDIA RENDERING ENGINE (Phase 7)
                # =========================================================================
                from app.media.compositor import TimelineCompositor
                from app.media.errors import FFmpegNotFoundError
                from app.media.ffmpeg import FFmpegService
                from app.media.workspace import MediaWorkspace
                from app.repositories.project import ProjectRepository
                from app.schemas.project_document import ProjectDocumentV1, create_default_project_document
                from app.services.project_service import ProjectService

                ffmpeg_svc = FFmpegService()
                if not ffmpeg_svc.is_available():
                    raise FFmpegNotFoundError(
                        "FFmpeg or FFprobe executable not found in system PATH. Cannot perform requested real media processing."
                    )

                # Resolve target ProjectDocumentV1
                document = None
                version_id_str = payload.get("version_id")

                if project_id_str and version_id_str:
                    proj_service = ProjectService(db)
                    try:
                        version = await proj_service.get_version(
                            uuid.UUID(version_id_str),
                            uuid.UUID(project_id_str),
                            job.workspace_id,
                        )
                        if version and version.document:
                            document = ProjectDocumentV1.model_validate(version.document)
                    except Exception as e:
                        logger.warning("Could not load ProjectVersion document: %s", e)

                if not document and "document" in payload:
                    document = ProjectDocumentV1.model_validate(payload["document"])

                if not document:
                    res_str = payload.get("resolution", "1080p")
                    res_dims = {"720p": (1280, 720), "1080p": (1920, 1080), "4k": (3840, 2160)}.get(res_str, (1920, 1080))
                    document = create_default_project_document(
                        aspect_ratio="16:9",
                        width=res_dims[0],
                        height=res_dims[1],
                        fps=int(payload.get("fps", 30)),
                    )

                # Execute real rendering via TimelineCompositor inside isolated MediaWorkspace
                async with MediaWorkspace(prefix=f"render_{job.id}_") as mws:
                    compositor = TimelineCompositor(ffmpeg_service=ffmpeg_svc)

                    async def _progress_cb(pct: int, stage_name: str, details: Optional[Dict[str, Any]] = None) -> None:
                        await job_service.update_progress(
                            job_id=job_id,
                            progress_percent=pct,
                            stage=stage_name,
                            message=f"Video render: {stage_name}",
                            details=details or {},
                        )

                    async def _cancellation_check() -> bool:
                        chk = await job_service.job_repo.get_by_id(job_id)
                        return chk is not None and chk.status == "cancelled"

                    render_result = await compositor.render_project(
                        document=document,
                        workspace_id=job.workspace_id,
                        db=db,
                        media_workspace=mws,
                        progress_callback=_progress_cb,
                        cancellation_checker=_cancellation_check,
                    )

                    # Stage: Ingesting into asset catalog and MinIO
                    await job_service.update_progress(
                        job_id=job_id,
                        progress_percent=95,
                        stage="uploading_output",
                        message="Ingesting rendered MP4 and thumbnail into storage catalog",
                    )

                    asset_mgr = AssetLifecycleManager(db)
                    video_asset = await asset_mgr.ingest_generated_asset(
                        workspace_id=job.workspace_id,
                        created_by=job.created_by,
                        content=render_result.video_path,
                        original_filename=f"render_{job.id}.mp4",
                        asset_type="video",
                        mime_type="video/mp4",
                        metadata={
                            "job_id": str(job.id),
                            "resolution": f"{render_result.canvas_profile.width}x{render_result.canvas_profile.height}",
                            "fps": render_result.canvas_profile.fps,
                            "duration_seconds": render_result.probe_result.duration_seconds,
                            "scenes_count": render_result.scenes_count,
                            "codec": render_result.probe_result.codec_name,
                            "bit_rate": render_result.probe_result.bit_rate,
                            "generated": True,
                        },
                    )

                    thumb_asset = await asset_mgr.ingest_generated_asset(
                        workspace_id=job.workspace_id,
                        created_by=job.created_by,
                        content=render_result.thumbnail_path,
                        original_filename=f"thumbnail_{job.id}.png",
                        asset_type="image",
                        mime_type="image/png",
                        metadata={
                            "job_id": str(job.id),
                            "generated": True,
                        },
                    )

                    # Update target Project status and thumbnail pointer
                    if project_id_str:
                        try:
                            proj_id = uuid.UUID(project_id_str)
                            project_repo = ProjectRepository(db)
                            project = await project_repo.get_by_id(proj_id, job.workspace_id)
                            if project:
                                project.thumbnail_asset_id = thumb_asset.id
                                project.status = "ready"
                                await project_repo.update(project)
                                await db.commit()
                        except Exception as proj_err:
                            logger.warning("Failed to update project status after real render: %s", proj_err)

                    result = {
                        "output_asset_id": str(video_asset.id),
                        "output_storage_key": video_asset.storage_key,
                        "thumbnail_asset_id": str(thumb_asset.id),
                        "thumbnail_storage_key": thumb_asset.storage_key,
                        "duration_seconds": render_result.probe_result.duration_seconds,
                        "resolution": f"{render_result.canvas_profile.width}x{render_result.canvas_profile.height}",
                        "fps": render_result.canvas_profile.fps,
                        "format": "mp4",
                        "codec": render_result.probe_result.codec_name,
                        "size_bytes": video_asset.size_bytes,
                    }
                    await job_service.mark_succeeded(
                        job_id=job_id,
                        result=result,
                        message="Video render completed successfully (Phase 7 Real Engine)",
                    )
                    return result

            # =========================================================================
            # MOCK PROVIDER EXECUTION (Deterministic fixtures for isolated test mode)
            # =========================================================================
            from app.media.ffmpeg import FFmpegService
            from app.media.fixtures import create_valid_mock_mp4_fixture, create_valid_mock_png_fixture
            from app.media.temp_manager import MediaTempManager
            from app.repositories.project import ProjectRepository

            async with MediaTempManager(job_id) as temp_dir:
                # Stage 2: Audio extraction & composition
                await job_service.update_progress(
                    job_id=job_id,
                    progress_percent=25,
                    stage="rendering_audio",
                    message="Rendering master audio track and mixing sound effects",
                    details={"audio_sample_rate": 48000, "channels": 2},
                )

                # Stage 3: Visual compositing
                await job_service.update_progress(
                    job_id=job_id,
                    progress_percent=60,
                    stage="rendering_visuals",
                    message="Compositing visual layers, avatar frames, and overlays",
                    details={"fps": 30, "resolution": "1920x1080"},
                )

                # Stage 4: Muxing output
                await job_service.update_progress(
                    job_id=job_id,
                    progress_percent=90,
                    stage="muxing_output",
                    message="Encoding H.264/AAC output stream into MP4 container",
                )

                total_duration = float(payload.get("total_duration", 10.0))
                res_str = payload.get("resolution", "1080p")
                res_dimensions = {"720p": (1280, 720), "1080p": (1920, 1080), "4k": (3840, 2160)}
                width, height = res_dimensions.get(res_str, (1920, 1080))
                fps = int(payload.get("fps", 30))

                scratch_file = temp_dir / f"render_{job.id}.mp4"
                thumbnail_file = temp_dir / f"thumbnail_{job.id}.png"

                # Generate structurally valid media fixtures
                create_valid_mock_mp4_fixture(
                    scratch_file,
                    duration_seconds=total_duration,
                    width=width,
                    height=height,
                )
                create_valid_mock_png_fixture(thumbnail_file, width=width, height=height)

                # Validate fixture structure via probe
                ffmpeg_svc = FFmpegService()
                probe_res = await ffmpeg_svc.probe(scratch_file, allow_mock_fallback=True)
                assert probe_res.duration_seconds > 0, "Rendered mock MP4 fixture must have positive duration"

                # Ingest rendered video and thumbnail via AssetLifecycleManager
                asset_mgr = AssetLifecycleManager(db)
                video_asset = await asset_mgr.ingest_generated_asset(
                    workspace_id=job.workspace_id,
                    created_by=job.created_by,
                    content=scratch_file,
                    original_filename=f"render_{job.id}.mp4",
                    asset_type="video",
                    mime_type="video/mp4",
                    metadata={
                        "job_id": str(job.id),
                        "resolution": f"{width}x{height}",
                        "fps": fps,
                        "duration_seconds": probe_res.duration_seconds,
                        "generated": True,
                    },
                )

                thumb_asset = await asset_mgr.ingest_generated_asset(
                    workspace_id=job.workspace_id,
                    created_by=job.created_by,
                    content=thumbnail_file,
                    original_filename=f"thumbnail_{job.id}.png",
                    asset_type="image",
                    mime_type="image/png",
                    metadata={
                        "job_id": str(job.id),
                        "generated": True,
                    },
                )

                # Update target Project status and thumbnail pointer
                if project_id_str:
                    try:
                        proj_id = uuid.UUID(project_id_str)
                        project_repo = ProjectRepository(db)
                        project = await project_repo.get_by_id(proj_id, job.workspace_id)
                        if project:
                            project.thumbnail_asset_id = thumb_asset.id
                            project.status = "ready"
                            await project_repo.update(project)
                            await db.commit()
                    except Exception as proj_err:
                        logger.warning("Failed to update project status after render: %s", proj_err)

                # Stage 5: Succeeded
                result = {
                    "output_asset_id": str(video_asset.id),
                    "output_storage_key": video_asset.storage_key,
                    "thumbnail_asset_id": str(thumb_asset.id),
                    "thumbnail_storage_key": thumb_asset.storage_key,
                    "duration_seconds": probe_res.duration_seconds,
                    "resolution": f"{width}x{height}",
                    "fps": fps,
                    "format": "mp4",
                    "codec": "h264",
                    "size_bytes": video_asset.size_bytes,
                }
                await job_service.mark_succeeded(
                    job_id=job_id,
                    result=result,
                    message="Video render completed successfully",
                )
                return result

        except Exception as exc:
            logger.error("Render failed for job %s: %s", job_id, exc)
            if project_id_str:
                try:
                    from app.repositories.project import ProjectRepository
                    proj_id = uuid.UUID(project_id_str)
                    project_repo = ProjectRepository(db)
                    project = await project_repo.get_by_id(proj_id, job.workspace_id)
                    if project and project.status == "processing":
                        project.status = "failed"
                        await project_repo.update(project)
                        await db.commit()
                except Exception:
                    pass

            await job_service.mark_failed(
                job_id=job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Video render failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.media.render_video",
    max_retries=3,
    default_retry_delay=10,
)
def render_video(self, job_id_str: str) -> Dict[str, Any]:
    """Celery task for video rendering on the cpu_media queue."""
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_render_video(job_id, task_id))
