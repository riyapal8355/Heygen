"""Job and JobEvent domain models representing asynchronous workloads, state machines, and audit ledgers."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Durable state-machine tracking asynchronous video, audio, lip-sync, and AI pipeline tasks."""

    __tablename__ = "jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this job",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who triggered or owns the job execution",
    )
    job_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Workload type: render_video, tts_synthesis, lip_sync, translate_project, voice_clone, avatar_train",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
        comment="State machine: queued, running, succeeded, failed, cancelled",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Queue priority score (higher executes first)",
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Client-provided key to prevent duplicate job executions",
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Overall execution progress from 0 to 100 percent",
    )
    stage: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Current execution stage (e.g. synthesizing_audio, generating_frames, complete)",
    )
    stage_message: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Human-readable stage progress description",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Input parameters and configuration required for job processing",
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Output results upon success (storage keys, duration, resolution, asset pointers)",
    )
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured failure information (error code, message, retryable status)",
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Asynchronous Celery task identifier for tracking and revocation",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of retry attempts executed",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        comment="Maximum permitted retries on transient errors",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when worker began processing the task",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when task terminated (succeeded, failed, cancelled)",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    events: Mapped[List["JobEvent"]] = relationship(
        "JobEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobEvent.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_jobs_workspace_status", "workspace_id", "status"),
        Index("ix_jobs_workspace_type", "workspace_id", "job_type"),
        Index("ix_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} type='{self.job_type}' status='{self.status}' progress={self.progress_percent}%>"


class JobEvent(Base):
    """Immutable audit event capturing stage transitions, progress, and failure diagnostics for a Job."""

    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Sequential event identifier",
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent job reference",
    )
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="progress_update",
        server_default="progress_update",
        comment="Event type: state_change, progress_update, warning, error",
    )
    from_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Previous job status before transition",
    )
    to_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="New job status after transition",
    )
    progress_percent: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Progress percentage reported at this event",
    )
    stage: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Pipeline stage active during this event",
    )
    message: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Human-readable event description",
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Additional diagnostic details or metrics",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp of event occurrence",
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="events")

    __table_args__ = (
        Index("ix_job_events_job_created", "job_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<JobEvent id={self.id} job_id={self.job_id} type='{self.event_type}' stage='{self.stage}'>"
