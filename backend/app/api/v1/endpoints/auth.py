"""Authentication endpoints: signup, login, token refresh, logout, and current user profile."""

from typing import Optional
from fastapi import APIRouter, Body, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    UserWithWorkspacesResponse,
    WorkspaceSummary,
)
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

REFRESH_COOKIE_NAME = "heyzen_refresh_token"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set secure HttpOnly cookie containing the raw refresh token."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE if not settings.DEBUG else False,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear refresh cookie upon logout."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE if not settings.DEBUG else False,
    )


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Atomically registers a new user, creates a personal workspace, and sets an HttpOnly refresh cookie.",
)
async def signup(
    payload: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    auth_service = AuthService(db)
    user, workspace, access_token, raw_refresh = await auth_service.signup(
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)

    _set_refresh_cookie(response, raw_refresh)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        workspace=WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            role="owner",
        ),
        tokens=TokenResponse(
            access_token=access_token,
            expires_in_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User Authentication",
    description="Authenticates credentials, starts a new session, and sets an HttpOnly refresh cookie.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    auth_service = AuthService(db)
    user, workspace, access_token, raw_refresh = await auth_service.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)

    _set_refresh_cookie(response, raw_refresh)

    ws_summary = None
    if workspace:
        ws_summary = WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            role="owner" if workspace.owner_id == user.id else "creator",
        )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        workspace=ws_summary,
        tokens=TokenResponse(
            access_token=access_token,
            expires_in_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Rotate Session & Access Token",
    description="Rotates the refresh token (session rotation) and issues a new access token.",
)
async def refresh_tokens(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = Body(default=None),
    heyzen_refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    token_candidate = heyzen_refresh_token or (payload.refresh_token if payload else None)
    if not token_candidate:
        try:
            body = await request.body()
            if body:
                import json
                data = json.loads(body)
                if isinstance(data, dict):
                    token_candidate = data.get("refresh_token")
        except Exception:
            pass

    auth_service = AuthService(db)
    user, new_access_token, new_raw_refresh = await auth_service.refresh(
        raw_refresh_token=token_candidate,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)

    _set_refresh_cookie(response, new_raw_refresh)

    ws_service = WorkspaceService(db)
    workspaces = await ws_service.list_user_workspaces(user.id)
    ws_summary = None
    if workspaces:
        ws, role = workspaces[0]
        ws_summary = WorkspaceSummary(id=ws.id, name=ws.name, slug=ws.slug, role=role)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        workspace=ws_summary,
        tokens=TokenResponse(
            access_token=new_access_token,
            expires_in_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Invalidates current refresh token session and clears the HttpOnly auth cookie.",
)
async def logout(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = Body(default=None),
    heyzen_refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    token_candidate = heyzen_refresh_token or (payload.refresh_token if payload else None)
    if not token_candidate:
        try:
            body = await request.body()
            if body:
                import json
                data = json.loads(body)
                if isinstance(data, dict):
                    token_candidate = data.get("refresh_token")
        except Exception:
            pass

    if token_candidate:
        auth_service = AuthService(db)
        await auth_service.logout(token_candidate)
        await db.commit()

    _clear_refresh_cookie(response)
    return LogoutResponse(status="ok", message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserWithWorkspacesResponse,
    summary="Current Authenticated User Profile",
    description="Returns the profile and workspace memberships of the authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserWithWorkspacesResponse:
    ws_service = WorkspaceService(db)
    workspaces = await ws_service.list_user_workspaces(current_user.id)

    summaries = [
        WorkspaceSummary(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            role=role,
        )
        for ws, role in workspaces
    ]

    return UserWithWorkspacesResponse(
        user=UserResponse.model_validate(current_user),
        workspaces=summaries,
    )
