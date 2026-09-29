"""Authentication domain service coordinating signup, login, session rotation, and logout."""

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException, ConflictException, RateLimitedException
from app.core.permissions import WorkspaceRole
from app.core.redis import check_rate_limit, reset_rate_limit
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository


class AuthService:
    """Encapsulates secure authentication workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.workspace_repo = WorkspaceRepository(session)
        self.settings = get_settings()

    def _hash_token(self, token: str) -> str:
        """Compute SHA-256 hash of a raw token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _generate_slug(self, name: str) -> str:
        """Create a URL-safe workspace slug with random suffix for uniqueness."""
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not base:
            base = "workspace"
        unique_suffix = secrets.token_hex(3)
        return f"{base[:40]}-{unique_suffix}"

    async def signup(
        self,
        email: str,
        display_name: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, Workspace, str, str]:
        """Atomically register a new user, create their personal workspace, and issue tokens."""
        # 1. Check if email already registered
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ConflictException(
                message="An account with this email address already exists.",
                code="AUTH_EMAIL_EXISTS",
            )

        # 2. Create User and Argon2id UserCredential
        user = await self.user_repo.create_user_with_password(
            email=email,
            display_name=display_name,
            password=password,
        )

        # 3. Create default personal workspace
        ws_name = f"{display_name}'s Workspace"
        slug = self._generate_slug(display_name)
        workspace = await self.workspace_repo.create_workspace(
            name=ws_name,
            slug=slug,
            owner_id=user.id,
        )

        # 4. Add user as Owner in workspace_members
        await self.workspace_repo.add_member(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER.value,
            status="active",
        )

        # 5. Issue JWT access token
        access_token = create_access_token(
            subject=str(user.id),
            claims={"workspace_id": str(workspace.id), "role": WorkspaceRole.OWNER.value},
        )

        # 6. Generate cryptographically secure refresh token & session record
        raw_refresh_token = secrets.token_urlsafe(48)
        refresh_hash = self._hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        await self.workspace_repo.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return user, workspace, access_token, raw_refresh_token

    async def login(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, Optional[Workspace], str, str]:
        """Authenticate user credentials and issue new session."""
        cleaned_email = email.strip().lower()

        # 1. Rate limiting checks (max 5 failed attempts per IP/email per minute; bypassed in test environment)
        ip_key = f"ratelimit:login:ip:{ip_address or 'unknown'}"
        email_key = f"ratelimit:login:email:{cleaned_email}"

        if self.settings.APP_ENV != "test":
            if not await check_rate_limit(ip_key, max_requests=10, window_seconds=60):
                raise RateLimitedException(
                    message="Too many login attempts from this IP. Please wait 1 minute.",
                    code="AUTH_RATE_LIMITED",
                )
            if not await check_rate_limit(email_key, max_requests=5, window_seconds=60):
                raise RateLimitedException(
                    message="Too many login attempts for this account. Please wait 1 minute.",
                    code="AUTH_RATE_LIMITED",
                )

        # 2. Look up user with credentials
        user = await self.user_repo.get_by_email(cleaned_email, load_credentials=True)
        if not user or not user.credential:
            raise AuthenticationException(
                message="Invalid email or password.",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # 3. Verify password hash
        if not verify_password(password, user.credential.password_hash):
            raise AuthenticationException(
                message="Invalid email or password.",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # 4. Check status
        if user.status != "active":
            raise AuthenticationException(
                message=f"Account is {user.status}. Please contact support.",
                code=f"AUTH_ACCOUNT_{user.status.upper()}",
            )

        # 5. Successful authentication: reset rate limits and update last_login_at
        await reset_rate_limit(ip_key)
        await reset_rate_limit(email_key)
        user.last_login_at = datetime.now(timezone.utc)

        # 6. Find default workspace
        workspaces = await self.workspace_repo.list_workspaces_for_user(user.id)
        default_workspace, role = workspaces[0] if workspaces else (None, "viewer")

        # 7. Issue tokens
        access_token = create_access_token(
            subject=str(user.id),
            claims={
                "workspace_id": str(default_workspace.id) if default_workspace else None,
                "role": role,
            },
        )

        raw_refresh_token = secrets.token_urlsafe(48)
        refresh_hash = self._hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        await self.workspace_repo.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return user, default_workspace, access_token, raw_refresh_token

    async def refresh(
        self,
        raw_refresh_token: Optional[str],
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Perform secure token rotation: validate session, revoke old token, issue new token pair."""
        if not raw_refresh_token:
            raise AuthenticationException(
                message="Refresh token is required.",
                code="AUTH_REFRESH_TOKEN_REQUIRED",
            )

        token_hash = self._hash_token(raw_refresh_token)
        session = await self.workspace_repo.get_session_by_hash(token_hash)

        if not session or not session.is_active:
            raise AuthenticationException(
                message="Invalid, expired, or revoked session. Please log in again.",
                code="AUTH_INVALID_SESSION",
            )

        user = session.user
        if not user or user.status != "active":
            raise AuthenticationException(
                message="User account is inactive.",
                code="AUTH_ACCOUNT_INACTIVE",
            )

        # 1. Revoke the old session (Rotation)
        await self.workspace_repo.revoke_session(session)

        # 2. Issue new raw refresh token and new session record
        new_raw_refresh = secrets.token_urlsafe(48)
        new_hash = self._hash_token(new_raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        await self.workspace_repo.create_session(
            user_id=user.id,
            refresh_token_hash=new_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # 3. Issue new access token
        access_token = create_access_token(subject=str(user.id))

        return user, access_token, new_raw_refresh

    async def logout(self, raw_refresh_token: Optional[str]) -> None:
        """Revoke active refresh session."""
        if raw_refresh_token:
            token_hash = self._hash_token(raw_refresh_token)
            session = await self.workspace_repo.get_session_by_hash(token_hash)
            if session and session.revoked_at is None:
                await self.workspace_repo.revoke_session(session)
