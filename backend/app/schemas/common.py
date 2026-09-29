"""Common schemas for standard API responses, errors, and health checks."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class APIError(BaseModel):
    """Machine-readable error details."""
    code: str = Field(..., description="Stable programmatic error code, e.g. NOT_FOUND, VALIDATION_ERROR")
    message: str = Field(..., description="Human-readable error description")
    request_id: Optional[str] = Field(None, description="Unique correlation request ID")
    details: Optional[Any] = Field(None, description="Detailed validation or contextual error details")


class APIErrorResponse(BaseModel):
    """Standard top-level error response envelope."""
    error: APIError


class HealthResponse(BaseModel):
    """Liveness probe response."""
    status: str = Field(default="ok", description="Liveness status indicator")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")


class ReadinessResponse(BaseModel):
    """Readiness probe response verifying dependencies."""
    status: str = Field(..., description="Readiness status: 'ready' or 'unhealthy'")
    checks: Dict[str, str] = Field(..., description="Dependency health statuses: database, redis, storage")


class AIHealthCapabilityStatus(BaseModel):
    """Health and model metadata for a specific AI capability."""
    capability: str = Field(..., description="Capability name: tts, asr, translation, image, avatar, video, llm")
    active_provider: str = Field(..., description="Active provider name")
    active_model: str = Field(..., description="Resolved model identifier")
    runtime_id: str = Field(..., description="Assigned execution runtime")
    device: str = Field(..., description="Compute device: cpu, cuda")
    status: str = Field(..., description="Capability health status: healthy, unavailable, or degraded")
    requires_gpu: bool = Field(False, description="Whether capability strictly requires GPU accelerator")


class AIHealthResponse(BaseModel):
    """AI Runtime and Hardware Health Probe response."""
    status: str = Field(..., description="Overall AI subsystem operational health")
    mode: str = Field(..., description="AI runtime mode: mock or real")
    hardware: Dict[str, Any] = Field(..., description="Host hardware specifications")
    runtimes: Dict[str, str] = Field(..., description="Compute runtimes health states (cpu, gpu)")
    capabilities: Dict[str, AIHealthCapabilityStatus] = Field(..., description="Per-capability status")
    gpu_worker: Optional[Dict[str, Any]] = Field(default_factory=dict, description="GPU worker and queue status")

