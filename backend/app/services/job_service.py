"""Job execution lifecycle and state-machine orchestration service."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models.job import Job, JobEvent
from app.repositories.job import JobEventRepository, JobRepository
from app.schemas.job import JobSubmitRequest

logger = get_logger(__name__)

VALID_JOB_TYPES = {
    "render_video": "heyzen.tasks.media.render_video",
    "tts_synthesis": "heyzen.tasks.ai.tts_synthesis",
    "lip_sync": "heyzen.tasks.ai.lip_sync",
    "generate_avatar_video": "heyzen.tasks.ai.lip_sync",
    "translate_project": "heyzen.tasks.ai.translate_project",
    "voice_clone": "heyzen.tasks.ai.voice_clone",
    "avatar_train": "heyzen.tasks.ai.avatar_train",
    "project_batch_speech": "heyzen.tasks.ai.project_batch_speech",
    "generate_scene_visual": "heyzen.tasks.ai.generate_scene_visual",
    "asr_transcription": "heyzen.tasks.ai.asr_transcription",
    "generate_project": "heyzen.tasks.ai.generate_project",
    "enhance_speech": "heyzen.tasks.ai.enhance_speech",
    "enhance_project_speech": "heyzen.tasks.ai.enhance_speech",
}


def resolve_job_queue(job_type: str, payload: Optional[Dict[str, Any]] = None) -> str:
    """Determine target Celery worker queue (cpu_media, gpu_ai, or maintenance).

    Routes CPU-compatible AI jobs (e.g. CPU TTS, translation, batch speech, ASR, LLM script generation, audio enhance) to 'cpu_media'
    so hosts without dedicated GPU workers can execute CPU AI tasks immediately.
    Routes GPU-dependent workloads (or explicit CUDA preference) to 'gpu_ai'.
    """
    if job_type.startswith("maintenance.") or job_type == "cleanup":
        return "maintenance"
    if job_type == "render_video":
        return "cpu_media"

    payload_data = payload or {}
    device_pref = str(payload_data.get("preferred_device") or payload_data.get("device") or "").lower()
    requires_gpu = bool(payload_data.get("requires_gpu", False))

    if device_pref == "cuda" or requires_gpu:
        return "gpu_ai"

    provider_pref = str(payload_data.get("provider") or "").lower()
    if provider_pref == "wav2lip":
        return "cpu_media"
    if provider_pref in ("musetalk", "stable_diffusion"):
        return "gpu_ai"

    # CPU-friendly AI workloads route to cpu_media unless CUDA is explicitly configured
    if job_type in ("tts_synthesis", "translate_project", "project_batch_speech", "asr_transcription", "generate_project", "enhance_speech", "enhance_project_speech", "voice_clone"):
        return "cpu_media"

    # Scene visual generation: routes to cpu_media for mock, otherwise gpu_ai for real neural diffusion
    if job_type == "generate_scene_visual":
        if provider_pref == "mock" or device_pref == "cpu":
            return "cpu_media"
        return "gpu_ai"

    # Neural vision/avatar tasks route to cpu_media if explicitly requested on CPU
    if device_pref == "cpu":
        return "cpu_media"

    return "gpu_ai"


async def publish_job_event_async(job_id: uuid.UUID, event_data: Dict[str, Any]) -> None:
    """Publish real-time job progress/status update over Redis pub/sub."""
    try:
        redis_client = await get_redis()
        channel = f"job:events:{job_id}"
        await redis_client.publish(channel, json.dumps(event_data, default=str))
    except Exception as exc:
        logger.warning("Failed to publish Redis event for job %s: %s", job_id, exc)


async def dispatch_job_webhook_event_async(
    workspace_id: uuid.UUID,
    job_id: uuid.UUID,
    event_type: str,
    payload_data: Dict[str, Any],
) -> None:
    """Asynchronously evaluate and trigger webhook deliveries for a job lifecycle event."""
    try:
        from app.db.session import async_session_factory
        from app.services.developer_service import DeveloperService

        async with async_session_factory() as db:
            dev_service = DeveloperService(db)
            event_id = f"evt_job_{job_id}_{event_type.replace('.', '_')}"
            await dev_service.dispatch_event_webhooks(
                workspace_id=workspace_id,
                event_id=event_id,
                event_type=event_type,
                payload_data=payload_data,
            )
    except Exception as exc:
        logger.warning("Failed to dispatch webhook for job %s (%s): %s", job_id, event_type, exc)


class JobService:
    """Orchestrates job state machine, idempotency, event auditing, and worker dispatch."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = JobRepository(db)
        self.event_repo = JobEventRepository(db)

    async def submit_job(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request: JobSubmitRequest,
    ) -> Tuple[Job, bool]:
        """Submit a new job or return existing active job if idempotency key matches.

        Returns: (job, created)
        """
        if request.job_type not in VALID_JOB_TYPES:
            raise AppException(
                status_code=400,
                code="INVALID_JOB_TYPE",
                message=f"Unsupported job type '{request.job_type}'. Must be one of: {list(VALID_JOB_TYPES.keys())}",
            )

        # 1. Idempotency verification
        if request.idempotency_key:
            existing = await self.job_repo.get_by_idempotency_key(
                workspace_id=workspace_id,
                idempotency_key=request.idempotency_key,
            )
            if existing:
                logger.info(
                    "Idempotent hit for workspace %s key %s -> Job %s",
                    workspace_id,
                    request.idempotency_key,
                    existing.id,
                )
                return existing, False

        # 2. Construct and persist Job entity
        job = Job(
            workspace_id=workspace_id,
            created_by=user_id,
            job_type=request.job_type,
            status="queued",
            priority=request.priority,
            idempotency_key=request.idempotency_key,
            progress_percent=0,
            stage="queued",
            stage_message="Job queued for processing",
            payload=request.payload,
            max_retries=request.max_retries,
        )
        await self.job_repo.create(job)

        # 3. Create initial JobEvent
        event = JobEvent(
            job_id=job.id,
            event_type="state_change",
            from_status=None,
            to_status="queued",
            progress_percent=0,
            stage="queued",
            message="Job queued for processing",
            details={"priority": request.priority, "payload_keys": list(request.payload.keys())},
        )
        await self.event_repo.create(event)
        await self.db.commit()

        # 4. Dispatch Celery task
        celery_task_name = VALID_JOB_TYPES[request.job_type]
        target_queue = resolve_job_queue(request.job_type, request.payload)
        try:
            from app.workers.celery_app import celery_app
            async_task = celery_app.send_task(
                celery_task_name,
                args=[str(job.id)],
                priority=request.priority,
                queue=target_queue,
                retry=False,
                ignore_result=True,
            )
            job.celery_task_id = async_task.id
            await self.job_repo.update(job)
            await self.db.commit()
        except Exception as exc:
            logger.warning(
                "Celery dispatch failed immediately for job %s: %s. Worker might poll or broker offline.",
                job.id,
                exc,
            )

        # 5. Broadcast to Redis pub/sub
        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "queued",
                "progress_percent": 0,
                "stage": "queued",
                "message": "Job queued for processing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await dispatch_job_webhook_event_async(
            job.workspace_id,
            job.id,
            "job.created",
            {"job_id": str(job.id), "status": "queued", "job_type": job.job_type},
        )

        return job, True

    async def get_job(self, job_id: uuid.UUID, workspace_id: Optional[uuid.UUID] = None) -> Job:
        """Fetch job strictly verifying workspace boundary if supplied."""
        job = await self.job_repo.get_by_id(job_id=job_id, workspace_id=workspace_id)
        if not job:
            raise NotFoundException(
                code="JOB_NOT_FOUND",
                message=f"Job '{job_id}' was not found in the specified workspace.",
            )
        return job

    async def list_jobs(
        self,
        workspace_id: uuid.UUID,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs for a given workspace with pagination and filters."""
        return await self.job_repo.list_by_workspace(
            workspace_id=workspace_id,
            job_type=job_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_job_events(
        self,
        job_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[JobEvent]:
        """Retrieve audit history for a job scoped to workspace."""
        await self.get_job(job_id, workspace_id)
        return await self.event_repo.list_by_job(job_id=job_id, limit=limit, offset=offset)

    async def cancel_job(
        self,
        job_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reason: str = "User requested cancellation",
    ) -> Job:
        """Cancel a running or queued job and revoke Celery task."""
        job = await self.get_job(job_id, workspace_id)

        if job.status in ("succeeded", "failed", "cancelled"):
            raise ConflictException(
                code="JOB_TERMINAL_STATE",
                message=f"Job '{job_id}' is already in terminal state '{job.status}' and cannot be cancelled.",
            )

        # Revoke Celery task if tracking id exists
        if job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception as exc:
                logger.warning("Revocation of Celery task %s failed: %s", job.celery_task_id, exc)

        old_status = job.status
        job.status = "cancelled"
        job.stage = "cancelled"
        job.stage_message = reason
        job.completed_at = datetime.now(timezone.utc)
        await self.job_repo.update(job)

        event = JobEvent(
            job_id=job.id,
            event_type="state_change",
            from_status=old_status,
            to_status="cancelled",
            progress_percent=job.progress_percent,
            stage="cancelled",
            message=reason,
            details={"cancelled_at": datetime.now(timezone.utc).isoformat()},
        )
        await self.event_repo.create(event)
        await self.db.commit()

        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "cancelled",
                "progress_percent": job.progress_percent,
                "stage": "cancelled",
                "message": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await dispatch_job_webhook_event_async(
            job.workspace_id,
            job.id,
            "job.cancelled",
            {"job_id": str(job.id), "status": "cancelled", "reason": reason},
        )
        return job

    # =========================================================================
    # Worker-facing methods
    # =========================================================================

    async def mark_started(
        self,
        job_id: uuid.UUID,
        stage: str = "initializing",
        message: str = "Worker started processing job",
        celery_task_id: Optional[str] = None,
    ) -> Job:
        """Called by worker to transition job from queued -> running."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundException(code="JOB_NOT_FOUND", message=f"Job {job_id} not found")

        old_status = job.status
        job.status = "running"
        job.stage = stage
        job.stage_message = message
        job.started_at = datetime.now(timezone.utc)
        if celery_task_id:
            job.celery_task_id = celery_task_id

        await self.job_repo.update(job)

        event = JobEvent(
            job_id=job.id,
            event_type="state_change",
            from_status=old_status,
            to_status="running",
            progress_percent=job.progress_percent,
            stage=stage,
            message=message,
            details={"started_at": job.started_at.isoformat()},
        )
        await self.event_repo.create(event)
        await self.db.commit()

        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "running",
                "progress_percent": job.progress_percent,
                "stage": stage,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await dispatch_job_webhook_event_async(
            job.workspace_id,
            job.id,
            "job.started",
            {"job_id": str(job.id), "status": "running", "stage": stage},
        )
        return job

    async def update_progress(
        self,
        job_id: uuid.UUID,
        progress_percent: int,
        stage: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Called by worker to record incremental progress updates."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundException(code="JOB_NOT_FOUND", message=f"Job {job_id} not found")

        if job.status != "running":
            # If cancelled while running, do not overwrite status
            return job

        job.progress_percent = min(100, max(0, progress_percent))
        job.stage = stage
        job.stage_message = message
        await self.job_repo.update(job)

        event = JobEvent(
            job_id=job.id,
            event_type="progress_update",
            from_status=job.status,
            to_status=job.status,
            progress_percent=job.progress_percent,
            stage=stage,
            message=message,
            details=details or {},
        )
        await self.event_repo.create(event)
        await self.db.commit()

        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "running",
                "progress_percent": job.progress_percent,
                "stage": stage,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return job

    async def mark_succeeded(
        self,
        job_id: uuid.UUID,
        result: Dict[str, Any],
        message: str = "Job completed successfully",
    ) -> Job:
        """Called by worker upon successful task completion."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundException(code="JOB_NOT_FOUND", message=f"Job {job_id} not found")

        old_status = job.status
        job.status = "succeeded"
        job.progress_percent = 100
        job.stage = "complete"
        job.stage_message = message
        job.result = result
        job.completed_at = datetime.now(timezone.utc)
        await self.job_repo.update(job)

        event = JobEvent(
            job_id=job.id,
            event_type="state_change",
            from_status=old_status,
            to_status="succeeded",
            progress_percent=100,
            stage="complete",
            message=message,
            details={"completed_at": job.completed_at.isoformat()},
        )
        await self.event_repo.create(event)
        await self.db.commit()

        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "succeeded",
                "progress_percent": 100,
                "stage": "complete",
                "message": message,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await dispatch_job_webhook_event_async(
            job.workspace_id,
            job.id,
            "job.succeeded",
            {"job_id": str(job.id), "status": "succeeded", "result": result},
        )
        return job

    async def mark_failed(
        self,
        job_id: uuid.UUID,
        error_details: Dict[str, Any],
        message: str = "Job execution failed",
    ) -> Job:
        """Called by worker when execution encounters unrecoverable error."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundException(code="JOB_NOT_FOUND", message=f"Job {job_id} not found")

        old_status = job.status
        job.status = "failed"
        job.stage = "failed"
        job.stage_message = message
        job.error_details = error_details
        job.completed_at = datetime.now(timezone.utc)
        await self.job_repo.update(job)

        event = JobEvent(
            job_id=job.id,
            event_type="state_change",
            from_status=old_status,
            to_status="failed",
            progress_percent=job.progress_percent,
            stage="failed",
            message=message,
            details=error_details,
        )
        await self.event_repo.create(event)
        await self.db.commit()

        await publish_job_event_async(
            job.id,
            {
                "job_id": str(job.id),
                "status": "failed",
                "progress_percent": job.progress_percent,
                "stage": "failed",
                "message": message,
                "error_details": error_details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await dispatch_job_webhook_event_async(
            job.workspace_id,
            job.id,
            "job.failed",
            {"job_id": str(job.id), "status": "failed", "error_details": error_details},
        )
        return job
