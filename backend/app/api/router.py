"""Top-level API router."""

from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router

root_api_router = APIRouter()

# Root-level health & readiness probes (/health, /ready)
root_api_router.include_router(health.router)

# Versioned API routes (/api/v1/...)
root_api_router.include_router(api_v1_router, prefix="/api/v1")
