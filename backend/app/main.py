import asyncio
import sys

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.api.middleware import RequestIDMiddleware
from app.api.router import root_api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis, init_redis
from app.db.session import close_db_engine
from app.schemas.common import APIError, APIErrorResponse

# Compatible status code for 422
STATUS_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)

settings = get_settings()
setup_logging(debug=settings.DEBUG)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager for startup initialization and graceful shutdown."""
    logger.info("Starting %s v%s in '%s' mode", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)
    # Validate production configuration fail-closed
    settings.validate_production_settings()
    # Initialize background connections
    await init_redis()
    # Ensure canonical global public presets are seeded
    from app.db.seeds import seed_canonical_presets, seed_development_fixtures
    try:
        await seed_canonical_presets()
        if settings.APP_ENV.lower() != "production":
            await seed_development_fixtures()
    except Exception as exc:
        logger.error("Failed to seed canonical presets or fixtures during startup: %s", exc)

    yield
    # Graceful cleanup
    logger.info("Shutting down %s...", settings.APP_NAME)
    await close_redis()
    await close_db_engine()
    logger.info("Shutdown complete.")


OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness probes, readiness checks, infrastructure pings, and AI runtime diagnostics.",
    },
    {
        "name": "Authentication",
        "description": "User registration, authentication, token refresh, and session management.",
    },
    {
        "name": "Workspaces",
        "description": "Multi-tenant workspace organization, members, invitations, and RBAC role assignments.",
    },
    {
        "name": "Projects",
        "description": "Video project lifecycle, canvas dimensions, metadata updates, and immutable version snapshots with OCC.",
    },
    {
        "name": "Project Orchestration",
        "description": "Video Agent AI generation, speech synthesis, project translation, scene visual generation, talking avatars, and video render pipeline.",
    },
    {
        "name": "Assets",
        "description": "Direct MinIO/S3 pre-signed upload intents, verification, streaming, and metadata management.",
    },
    {
        "name": "Avatars",
        "description": "Preset and custom talking avatar actors, looks, and preview catalogs.",
    },
    {
        "name": "Voices",
        "description": "TTS voice catalog, voice cloning, audio preview playback, and custom speaker profiles.",
    },
    {
        "name": "Templates",
        "description": "Reusable multi-scene video templates, presets, and category blueprints.",
    },
    {
        "name": "Brand Kits",
        "description": "Workspace brand guidelines, colors, typography, logos, and terminology glossaries.",
    },
    {
        "name": "Jobs",
        "description": "Asynchronous background rendering tasks, AI pipelines, progress monitoring, and real-time SSE streaming.",
    },
    {
        "name": "Ask Rhys AI",
        "description": "Conversational AI copilot assistance, video design advice, and project suggestions.",
    },
    {
        "name": "API Keys",
        "description": "Developer API keys, secret key issuance, scoped permissions, and access controls.",
    },
    {
        "name": "Webhooks",
        "description": "Real-time webhook subscriptions, event delivery logs, HMAC signature verification, and redelivery.",
    },
    {
        "name": "Folders",
        "description": "Project organization folders within workspaces.",
    },
    {
        "name": "Invitations",
        "description": "Workspace member invitation redemption.",
    },
    {
        "name": "Developer",
        "description": "Developer platform capabilities: scoped API key management, HMAC webhook subscriptions, delivery audit history, and webhook test ping.",
    },
    {
        "name": "Studio",
        "description": "Interactive Studio document engine, multi-layer canvas composition, optimistic concurrency control (OCC), and version snapshots.",
    },
    {
        "name": "Media",
        "description": "Media asset storage lifecycle, direct MinIO/S3 pre-signed upload intents, verification, and streaming.",
    },
    {
        "name": "Audio",
        "description": "Audio timeline tracks, TTS voice synthesis, voice cloning, audio preview playback, and speech enhancement.",
    },
    {
        "name": "AI",
        "description": "Autonomous Video Agent generation, neural speech synthesis, project translation, scene visual generation, talking avatars, and Rhys AI Copilot.",
    },
    {
        "name": "Rendering",
        "description": "Composite timeline validation, preflight diagnostics, and video render export pipeline.",
    },
]


def create_application() -> FastAPI:
    """Application factory configuring middleware, exception handlers, and routers."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="HeyZen Autonomous AI Video Creation & Studio Backend API",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_tags=OPENAPI_TAGS,
    )

    # 1. Request ID Middleware (Outer-most to wrap all operations)
    app.add_middleware(RequestIDMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    # 3. Standardized Central Error Handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        payload = APIErrorResponse(
            error=APIError(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                details=exc.details,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        status_code = exc.status_code
        error_code = {
            status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_409_CONFLICT: "CONFLICT",
            STATUS_422: "VALIDATION_ERROR",
            status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
        }.get(status_code, "HTTP_ERROR")

        payload = APIErrorResponse(
            error=APIError(
                code=error_code,
                message=str(exc.detail),
                request_id=request_id,
            )
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        payload = APIErrorResponse(
            error=APIError(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                request_id=request_id,
                details=exc.errors(),
            )
        )
        return JSONResponse(
            status_code=STATUS_422,
            content=payload.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled server exception on %s: %s", request.url.path, exc)
        message = str(exc) if settings.DEBUG else "An internal server error occurred."
        payload = APIErrorResponse(
            error=APIError(
                code="INTERNAL_SERVER_ERROR",
                message=message,
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(),
        )

    # 4. Mount Routers
    app.include_router(root_api_router)

    return app


app = create_application()
