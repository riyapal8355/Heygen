"""Tests for PostgreSQL async database connection, models, and constraints."""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import ping_db
from app.models.user import User, UserCredential
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_database_connectivity():
    """Verify live async database ping against PostgreSQL container."""
    is_connected = await ping_db()
    assert is_connected is True, "Database ping failed to return 1"


@pytest.mark.asyncio
async def test_user_creation_and_query(db_session: AsyncSession):
    """Verify creating a User and UserCredential within an isolated transaction."""
    repo = UserRepository(db_session)
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    user = await repo.create_user_with_password(
        email=unique_email,
        display_name="Test Developer",
        password="TestPassword123!",
    )

    assert user.id is not None
    assert user.email == unique_email
    assert user.display_name == "Test Developer"
    assert user.status == "active"
    assert user.created_at is not None

    # Fetch user back with credentials
    fetched = await repo.get_by_email(unique_email, load_credentials=True)
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.credential is not None
    assert fetched.credential.password_hash.startswith("$argon2id$")
    assert fetched.credential.is_active is True


@pytest.mark.asyncio
async def test_email_normalization(db_session: AsyncSession):
    """Verify email is trimmed and lowercased automatically."""
    user = User(
        email="  Alice.Smith@Example.COM  ",
        display_name="Alice Smith",
    )
    assert user.email == "alice.smith@example.com"


@pytest.mark.asyncio
async def test_invalid_email_raises():
    """Verify invalid email string raises ValueError."""
    with pytest.raises(ValueError):
        User(email="notanemail", display_name="Bad User")
