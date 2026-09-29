"""Job management, async task orchestration, and SSE streaming API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.job import (
    JobCancelResponse,
    JobEventResponse,
    JobResponse,
    JobSubmitRequest,
)
from app.services.job_service import JobService
from app.services.sse_service import stream_job_events

router = APIRouter(tags=["Jobs"])


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Job",
    description="Enqueue an asynchronous task pipeline job with optional idempotency key.",
)
async def submit_job(
    payload: JobSubmitRequest,
    response: Response,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    workspace, _ = context
    service = JobService(db)
    job, created = await service.submit_job(
        workspace_id=workspace.id,
        user_id=current_user.id,
        request=payload,
    )
    if not created:
        response.status_code = status.HTTP_200_OK

    return JobResponse.model_validate(job)


@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List Jobs",
    description="List background jobs in the current workspace with optional type and status filtering.",
)
async def list_jobs(
    job_type: Optional[str] = Query(None, description="Filter by workload type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.read")),
    db: AsyncSession = Depends(get_db),
) -> List[JobResponse]:
    workspace, _ = context
    service = JobService(db)
    jobs = await service.list_jobs(
        workspace_id=workspace.id,
        job_type=job_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [JobResponse.model_validate(j) for j in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get Job",
    description="Fetch a job by ID within the active workspace.",
)
async def get_job(
    job_id: uuid.UUID = Path(..., description="Target Asynchronous Job UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.read")),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    workspace, _ = context
    service = JobService(db)
    job = await service.get_job(job_id=job_id, workspace_id=workspace.id)
    return JobResponse.model_validate(job)


@router.get(
    "/jobs/{job_id}/events",
    response_model=List[JobEventResponse],
    summary="Get Job Audit Events",
    description="Retrieve chronological lifecycle and progress events for a job.",
)
async def get_job_events(
    job_id: uuid.UUID = Path(..., description="Target Asynchronous Job UUID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.read")),
    db: AsyncSession = Depends(get_db),
) -> List[JobEventResponse]:
    workspace, _ = context
    service = JobService(db)
    events = await service.get_job_events(
        job_id=job_id,
        workspace_id=workspace.id,
        limit=limit,
        offset=offset,
    )
    return [JobEventResponse.model_validate(e) for e in events]


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobCancelResponse,
    summary="Cancel Job",
    description="Cancel a running or queued job and revoke the associated Celery task.",
)
async def cancel_job(
    job_id: uuid.UUID = Path(..., description="Target Asynchronous Job UUID"),
    reason: str = Query("User requested cancellation", description="Cancellation reason"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.cancel")),
    db: AsyncSession = Depends(get_db),
) -> JobCancelResponse:
    workspace, _ = context
    service = JobService(db)
    job = await service.cancel_job(
        job_id=job_id,
        workspace_id=workspace.id,
        reason=reason,
    )
    return JobCancelResponse(
        job_id=job.id,
        status=job.status,
        message="Job successfully cancelled.",
    )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream Job Progress (SSE)",
    description="Subscribe to live real-time Server-Sent Events (SSE) updates for a job via Redis Pub/Sub.",
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Real-time Server-Sent Events (SSE) stream yielding live job progress and transition events.",
        }
    },
)
async def stream_job_progress(
    job_id: uuid.UUID = Path(..., description="Target Asynchronous Job UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.read")),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    workspace, _ = context
    from app.repositories.job import JobRepository
    job = await JobRepository(db).get_by_id(job_id, workspace.id)
    if not job:
        raise NotFoundException(
            code="JOB_NOT_FOUND",
            message=f"Job '{job_id}' not found in this workspace.",
        )
    return StreamingResponse(
        stream_job_events(job_id=job_id, workspace_id=workspace.id, db=db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
