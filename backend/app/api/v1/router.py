"""API v1 Router aggregating all domain sub-routers."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    assets,
    auth,
    avatars,
    brand_kits,
    developer,
    folders,
    health,
    invitations,
    jobs,
    project_orchestration,
    projects,
    templates,
    voices,
    workspaces,
    ask_rhys,
)

api_v1_router = APIRouter()

# Register v1 domain sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(workspaces.router)
api_v1_router.include_router(developer.router)
api_v1_router.include_router(invitations.router)
api_v1_router.include_router(folders.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(project_orchestration.router)
api_v1_router.include_router(assets.router)
api_v1_router.include_router(avatars.router)
api_v1_router.include_router(voices.router)
api_v1_router.include_router(templates.router)
api_v1_router.include_router(brand_kits.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(ask_rhys.router)
api_v1_router.include_router(ask_rhys.direct_router)


