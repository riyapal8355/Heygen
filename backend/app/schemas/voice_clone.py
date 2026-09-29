"""Schemas for voice cloning requests, jobs, and results."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class VoiceCloneRequest(BaseModel):
    """Payload to initiate an asynchronous voice cloning job."""

    name: str = Field(..., min_length=1, max_length=128, description="Display name for the cloned voice")
    reference_asset_id: uuid.UUID = Field(..., description="ID of the audio Asset to use as reference speaker sample")
    language: Optional[str] = Field("en", max_length=16, description="Target language code (e.g., 'en', 'es', 'zh')")
    description: Optional[str] = Field(None, max_length=512, description="Optional description of voice style/tone")
    gender: Optional[str] = Field("neutral", max_length=16, description="Perceived voice gender (male, female, neutral)")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional model inference options")


class VoiceCloneJobResponse(BaseModel):
    """Response returned when a voice cloning job is accepted."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID = Field(..., description="Durable job tracking ID")
    voice_id: uuid.UUID = Field(..., description="Pre-allocated voice record ID")
    status: str = Field(..., description="Current job status (queued, running, etc.)")
    voice_name: str = Field(..., description="Cloned voice name")
    workspace_id: uuid.UUID = Field(..., description="Owning workspace ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class VoiceCloneResult(BaseModel):
    """Final result payload populated on the job upon completion."""

    voice_id: str
    name: str
    language: str
    provider: str
    model: str
    reference_asset_id: str
    embedding_storage_key: str
    preview_asset_id: Optional[str] = None
    sample_duration_seconds: float
    cloning_latency_ms: float
    status: str
