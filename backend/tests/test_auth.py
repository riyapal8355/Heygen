"""Comprehensive test suite for Authentication, Sign Up, Login, Token Refresh, and Logout."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserCredential, UserSession


@pytest.mark.asyncio
async def test_signup_success(async_client: AsyncClient, db_session: AsyncSession):
    """Verify signup creates user, personal workspace, sets Owner role, and issues tokens + cookie."""
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "display_name": "Dr. Video",
        "password": "SecurePassword123!",
    }

    response = await async_client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "user" in data
    assert data["user"]["email"] == unique_email.lower()
    assert data["user"]["display_name"] == "Dr. Video"
    assert data["user"]["status"] == "active"

    assert "workspace" in data
    assert data["workspace"] is not None
    assert data["workspace"]["role"] == "owner"
    assert "tokens" in data
    assert "access_token" in data["tokens"]

    # Verify HttpOnly refresh cookie is returned in response
    assert "heyzen_refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(async_client: AsyncClient):
    """Verify signup with an already registered email returns 409 Conflict."""
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "display_name": "First User",
        "password": "Password123!",
    }
    r1 = await async_client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201

    r2 = await async_client.post("/api/v1/auth/signup", json=payload)
    assert r2.status_code == 409
    err = r2.json()
    assert err["error"]["code"] == "AUTH_EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_password_is_hashed_and_not_plaintext(async_client: AsyncClient):
    """Verify raw password is never stored in database and Argon2id hash is used."""
    unique_email = f"argon_{uuid.uuid4().hex[:8]}@example.com"
    raw_pass = "MySecretPassphrase123!"
    r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "display_name": "Argon Tester", "password": raw_pass},
    )
    assert r.status_code == 201

    # Query credentials directly via session factory
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        stmt = (
            select(UserCredential)
            .join(User, User.id == UserCredential.user_id)
            .where(User.email == unique_email.lower())
        )
        res = await session.execute(stmt)
        cred = res.scalar_one()
        assert cred.password_hash != raw_pass
        assert cred.password_hash.startswith("$argon2id$")


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Verify login with correct credentials returns tokens and sets cookie."""
    unique_email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    # 1. Sign up
    await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "display_name": "Login User", "password": password},
    )

    # 2. Log in
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["email"] == unique_email
    assert data["tokens"]["access_token"] is not None
    assert "heyzen_refresh_token" in login_resp.cookies


@pytest.mark.asyncio
async def test_login_invalid_password_rejected(async_client: AsyncClient):
    """Verify wrong password returns 401 generic error."""
    unique_email = f"wrong_{uuid.uuid4().hex[:8]}@example.com"
    await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "display_name": "Wrong Pass", "password": "CorrectPassword123!"},
    )

    r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword999!"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_email_generic_failure(async_client: AsyncClient):
    """Verify nonexistent email returns same generic 401 error without leaking presence."""
    r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody_exists_here_9876@example.com", "password": "AnyPassword123!"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_suspended_user_rejected(async_client: AsyncClient):
    """Verify suspended user cannot log in."""
    unique_email = f"suspended_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "display_name": "Suspended User", "password": password},
    )
    assert r.status_code == 201

    # Suspend user directly in database
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        user_stmt = select(User).where(User.email == unique_email)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one()
        user.status = "suspended"
        await session.commit()

    # Attempt login
    login_r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_r.status_code == 401
    assert "ACCOUNT_SUSPENDED" in login_r.json()["error"]["code"]


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_old_token_invalidation(async_client: AsyncClient):
    """Verify session rotation: refreshing invalidates the previous refresh token."""
    email = f"rotate_{uuid.uuid4().hex[:8]}@example.com"
    r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Rotator", "password": "Password123!"},
    )
    assert r.status_code == 201
    initial_refresh_cookie = r.cookies.get("heyzen_refresh_token")
    assert initial_refresh_cookie is not None

    # 1. Refresh using initial cookie
    refresh_resp_1 = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"heyzen_refresh_token": initial_refresh_cookie},
    )
    assert refresh_resp_1.status_code == 200
    new_refresh_cookie = refresh_resp_1.cookies.get("heyzen_refresh_token")
    assert new_refresh_cookie is not None
    assert new_refresh_cookie != initial_refresh_cookie

    # 2. Attempt to reuse old initial refresh token -> must fail (rotated / revoked)
    reuse_resp = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"heyzen_refresh_token": initial_refresh_cookie},
    )
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["error"]["code"] == "AUTH_INVALID_SESSION"

    # 3. New refresh cookie still works
    refresh_resp_2 = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"heyzen_refresh_token": new_refresh_cookie},
    )
    assert refresh_resp_2.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_session(async_client: AsyncClient):
    """Verify logout revokes the session and subsequent refresh fails."""
    email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Logout Tester", "password": "Password123!"},
    )
    cookie = r.cookies.get("heyzen_refresh_token")

    # Logout
    logout_r = await async_client.post(
        "/api/v1/auth/logout",
        cookies={"heyzen_refresh_token": cookie},
    )
    assert logout_r.status_code == 200

    # Subsequent refresh with that token fails
    refresh_r = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"heyzen_refresh_token": cookie},
    )
    assert refresh_r.status_code == 401


@pytest.mark.asyncio
async def test_get_me_endpoints(async_client: AsyncClient):
    """Verify /api/v1/auth/me requires auth and returns current user with workspaces."""
    # 1. Unauthenticated -> 401
    unauth_r = await async_client.get("/api/v1/auth/me")
    assert unauth_r.status_code == 401

    # 2. Authenticated -> 200
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    signup_r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Current User", "password": "Password123!"},
    )
    access_token = signup_r.json()["tokens"]["access_token"]

    auth_r = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert auth_r.status_code == 200
    me_data = auth_r.json()
    assert me_data["user"]["email"] == email
    assert len(me_data["workspaces"]) >= 1
    assert me_data["workspaces"][0]["role"] == "owner"
