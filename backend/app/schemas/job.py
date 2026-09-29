"""Pydantic V2 schemas for Job execution, status, and event audit logs."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobSubmitRequest(BaseModel):
    """Payload schema for requesting asynchronous job execution."""

    job_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Type of workload: render_video, tts_synthesis, lip_sync, translate_project, voice_clone, avatar_train",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters, configuration, and inputs required for the worker task",
    )
    priority: int = Field(
        10,
        ge=1,
        le=100,
        description="Queue priority score (higher executes first)",
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=255,
        description="Client-supplied idempotency key to prevent duplicate job creation",
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts on transient failure",
    )


class JobEventResponse(BaseModel):
    """Read model for individual job audit and lifecycle events."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: uuid.UUID
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    progress_percent: Optional[int] = None
    stage: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class JobResponse(BaseModel):
    """Read model for durable Job entities with progress, results, and diagnostics."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    job_type: str
    status: str
    priority: int
    idempotency_key: Optional[str] = None
    progress_percent: int
    stage: Optional[str] = None
    stage_message: Optional[str] = None
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    celery_task_id: Optional[str] = None
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobCancelResponse(BaseModel):
    """Response payload when a job cancellation is requested."""

    job_id: uuid.UUID
    status: str
    message: str
