"""Pytest fixtures for HeyZen backend testing."""

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.redis import close_redis
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def test_settings() -> Settings:
    """Return application settings configured for testing."""
    import os
    from pathlib import Path
    s = get_settings()
    s.APP_ENV = "test"
    if not os.path.isdir(s.AI_MODEL_CACHE_DIR):
        backend_cache = Path(__file__).resolve().parent.parent / "models_cache"
        if backend_cache.is_dir():
            s.AI_MODEL_CACHE_DIR = str(backend_cache)
    return s


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous test HTTP client configured against the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session that always rolls back to prevent persistent side-effects."""
    settings = get_settings()
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        async with session_factory() as session:
            yield session
            await transaction.rollback()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Provide an isolated test user entity."""
    import uuid
    from app.models.user import User
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        display_name="Test User",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user) -> "Workspace":
    """Provide an isolated test workspace entity owned by test_user."""
    import uuid
    from app.models.workspace import Workspace, WorkspaceMember
    ws = Workspace(
        name="Test Workspace",
        slug=f"test-ws-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
        status="active",
    )
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=test_user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.flush()
    return ws


@pytest_asyncio.fixture(autouse=True)
async def cleanup_connections():
    """Ensure background connections and test rate limits are cleanly cleared between tests."""
    yield
    from app.db.session import async_engine
    from app.core.redis import get_redis, close_redis
    await async_engine.dispose()
    try:
        r = await get_redis()
        keys = await r.keys("ratelimit:*")
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
    await close_redis()
