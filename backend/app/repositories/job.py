"""Job and JobEvent repository for workspace-scoped task state management."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobEvent


class JobRepository:
    """Data access operations for Job state machine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        job_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> Optional[Job]:
        """Fetch job by ID, optionally enforcing workspace isolation."""
        query = select(Job).where(Job.id == job_id)
        if workspace_id is not None:
            query = query.where(Job.workspace_id == workspace_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_idempotency_key(
        self,
        workspace_id: uuid.UUID,
        idempotency_key: str,
    ) -> Optional[Job]:
        """Fetch active job matching workspace idempotency key (excluding failed/cancelled)."""
        query = select(Job).where(
            Job.workspace_id == workspace_id,
            Job.idempotency_key == idempotency_key,
            ~Job.status.in_(["failed", "cancelled"]),
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs in a workspace with optional status/type filtering."""
        query = select(Job).where(Job.workspace_id == workspace_id)
        if job_type:
            query = query.where(Job.job_type == job_type)
        if status:
            query = query.where(Job.status == status)

        query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, job: Job) -> Job:
        """Persist a new job entity."""
        self.db.add(job)
        await self.db.flush()
        return job

    async def update(self, job: Job) -> Job:
        """Update job timestamps and flush."""
        job.updated_at = datetime.now(timezone.utc)
        self.db.add(job)
        await self.db.flush()
        return job


class JobEventRepository:
    """Data access operations for immutable JobEvent audit records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: JobEvent) -> JobEvent:
        """Persist a job lifecycle or progress audit event."""
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_by_job(
        self,
        job_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[JobEvent]:
        """Fetch chronological event log for a given job."""
        query = (
            select(JobEvent)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at.asc(), JobEvent.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
