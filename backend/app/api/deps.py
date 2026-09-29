"""FastAPI dependency injection for authentication, workspace resolution, and RBAC authorization."""

import uuid
from typing import Any, Callable, Optional, Tuple
import jwt
from fastapi import Depends, Header, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationException, ForbiddenException, NotFoundException
from app.core.permissions import WorkspaceRole, has_permission, is_role_at_least
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository

# Bearer token scheme for OpenAPI documentation
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    token_query: Optional[str] = Query(None, alias="token", description="Short-lived access token for browser EventSource / SSE"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT access token from Authorization header or SSE query parameter and return active User."""
    raw_token: Optional[str] = None
    if auth and auth.credentials:
        raw_token = auth.credentials
    elif token_query:
        raw_token = token_query

    if not raw_token:
        raise AuthenticationException(
            message="Authentication credentials were not provided.",
            code="AUTH_UNAUTHORIZED",
        )

    # Reject API keys and webhook secrets from user JWT flows and SSE tokens
    if raw_token.startswith("hz_") or raw_token.startswith("whsec_"):
        raise AuthenticationException(
            message="API keys and webhook secrets cannot be used as user tokens.",
            code="AUTH_INVALID_TOKEN_TYPE",
        )

    try:
        payload = decode_token(raw_token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationException(
            message="Access token has expired. Please refresh your session.",
            code="AUTH_TOKEN_EXPIRED",
        )
    except jwt.PyJWTError:
        raise AuthenticationException(
            message="Invalid authentication token.",
            code="AUTH_INVALID_TOKEN",
        )

    if payload.get("type") != "access":
        raise AuthenticationException(
            message="Invalid token type. Expected access token.",
            code="AUTH_INVALID_TOKEN_TYPE",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationException(message="Token missing subject claim.", code="AUTH_INVALID_TOKEN")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException(message="Malformed user ID claim in token.", code="AUTH_INVALID_TOKEN")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise AuthenticationException(message="User account no longer exists.", code="AUTH_USER_NOT_FOUND")

    if user.status != "active":
        raise AuthenticationException(
            message=f"User account is {user.status}.",
            code=f"AUTH_ACCOUNT_{user.status.upper()}",
        )

    return user


async def get_api_key_context(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Any, Workspace]:
    """Extract and authenticate API key, enforcing workspace boundary isolation."""
    from app.services.developer_service import DeveloperService

    raw_key: Optional[str] = None
    if x_api_key and x_api_key.strip():
        raw_key = x_api_key.strip()
    elif auth and auth.credentials and auth.credentials.startswith("hz_"):
        raw_key = auth.credentials.strip()

    if not raw_key:
        raise AuthenticationException(
            message="API key credentials were not provided.",
            code="AUTH_UNAUTHORIZED",
        )

    service = DeveloperService(db)
    api_key, workspace = await service.authenticate_api_key(raw_key)

    # Verify workspace isolation if route contains workspace_id
    path_ws_id = request.path_params.get("workspace_id")
    if path_ws_id:
        try:
            expected_uuid = uuid.UUID(str(path_ws_id))
            if expected_uuid != workspace.id:
                raise ForbiddenException(
                    message="API key does not have access to the specified workspace.",
                    code="WORKSPACE_FORBIDDEN",
                )
        except ValueError:
            raise NotFoundException(message="Invalid workspace ID in URL path.", code="WORKSPACE_INVALID_ID")

    return api_key, workspace


async def get_current_workspace(
    request: Request,
    workspace_id_query: Optional[str] = Query(None, alias="workspace_id", description="Optional workspace ID query parameter fallback"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID", description="Optional workspace context header (must match workspace_id path parameter if both provided)"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Developer API key (hz_...)"),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    token_query: Optional[str] = Query(None, alias="token", description="Access token query parameter for EventSource / SSE"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Workspace, WorkspaceMember]:
    """Resolve target workspace from path, query, header, or API key, and verify permissions."""
    is_api_key = bool(
        (x_api_key and x_api_key.strip().startswith("hz_")) or
        (auth and auth.credentials and auth.credentials.startswith("hz_"))
    )

    if is_api_key:
        api_key, workspace = await get_api_key_context(request, auth, x_api_key, db)
        role = WorkspaceRole.ADMIN.value if api_key.permissions == "full" else WorkspaceRole.VIEWER.value
        synthetic_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=api_key.created_by or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            role=role,
            status="active",
        )
        return workspace, synthetic_member

    current_user = await get_current_user(auth=auth, token_query=token_query, db=db)

    path_ws_id = request.path_params.get("workspace_id")
    resolved_id: Optional[uuid.UUID] = None

    if path_ws_id:
        try:
            resolved_id = uuid.UUID(str(path_ws_id))
        except ValueError:
            raise NotFoundException(message="Invalid workspace ID in URL path.", code="WORKSPACE_INVALID_ID")

        # If both path workspace_id and X-Workspace-ID header are provided, verify they match
        if x_workspace_id:
            try:
                header_ws_id = uuid.UUID(x_workspace_id)
                if resolved_id != header_ws_id:
                    raise ForbiddenException(
                        message="X-Workspace-ID header does not match workspace ID in URL path.",
                        code="WORKSPACE_MISMATCH",
                    )
            except ValueError:
                raise NotFoundException(message="Invalid X-Workspace-ID header format.", code="WORKSPACE_INVALID_ID")

    elif x_workspace_id:
        try:
            resolved_id = uuid.UUID(x_workspace_id)
        except ValueError:
            raise NotFoundException(message="Invalid X-Workspace-ID header format.", code="WORKSPACE_INVALID_ID")
    elif workspace_id_query:
        try:
            resolved_id = uuid.UUID(workspace_id_query)
        except ValueError:
            raise NotFoundException(message="Invalid workspace_id query parameter.", code="WORKSPACE_INVALID_ID")

    path_job_id = request.path_params.get("job_id")
    if path_job_id:
        try:
            from app.repositories.job import JobRepository
            job_uuid = uuid.UUID(str(path_job_id))
            job = await JobRepository(db).get_by_id(job_uuid)
            if job:
                if resolved_id is not None and resolved_id != job.workspace_id:
                    raise NotFoundException(
                        message="Job was not found in the specified workspace.",
                        code="JOB_NOT_FOUND",
                    )
                resolved_id = job.workspace_id
        except (NotFoundException, ForbiddenException):
            raise
        except Exception:
            pass

    ws_repo = WorkspaceRepository(db)

    # If no explicit workspace provided, fallback to the user's primary/first workspace
    if resolved_id is None:
        workspaces = await ws_repo.list_workspaces_for_user(current_user.id)
        if not workspaces:
            raise NotFoundException(
                message="User does not belong to any active workspace.",
                code="WORKSPACE_NONE_AVAILABLE",
            )
        resolved_id = workspaces[0][0].id

    workspace = await ws_repo.get_by_id(resolved_id)
    if not workspace:
        raise NotFoundException(message="Workspace not found.", code="WORKSPACE_NOT_FOUND")

    # Verify caller is an active member
    member = await ws_repo.get_member(workspace.id, current_user.id)
    if not member or member.status != "active":
        raise ForbiddenException(
            message="You do not have access to this workspace.",
            code="WORKSPACE_FORBIDDEN",
        )

    return workspace, member


def require_permission(permission: str) -> Callable:
    """Dependency factory checking that caller's workspace role grants the specified permission."""

    async def permission_checker(
        workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(get_current_workspace),
    ) -> Tuple[Workspace, WorkspaceMember]:
        workspace, member = workspace_context
        if not has_permission(member.role, permission):
            raise ForbiddenException(
                message=f"Permission '{permission}' is required to perform this action.",
                code="INSUFFICIENT_PERMISSIONS",
            )
        return workspace, member

    return permission_checker


def require_role(minimum_role: WorkspaceRole) -> Callable:
    """Dependency factory verifying caller's role meets or exceeds minimum_role hierarchy."""

    async def role_checker(
        workspace_context: Tuple[Workspace, WorkspaceMember] = Depends(get_current_workspace),
    ) -> Tuple[Workspace, WorkspaceMember]:
        workspace, member = workspace_context
        if not is_role_at_least(member.role, minimum_role.value):
            raise ForbiddenException(
                message=f"Role '{minimum_role.value}' or higher is required.",
                code="INSUFFICIENT_ROLE",
            )
        return workspace, member

    return role_checker
