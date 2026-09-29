"""Tests for Redis connection and basic caching operations."""

import uuid
import pytest
from app.core.redis import get_redis, ping_redis


@pytest.mark.asyncio
async def test_redis_connectivity():
    """Verify live async ping to Redis container."""
    is_connected = await ping_redis()
    assert is_connected is True, "Redis ping failed to respond PONG"


@pytest.mark.asyncio
async def test_redis_set_get():
    """Verify standard async key-value caching in Redis."""
    client = await get_redis()
    test_key = f"heyzen:test:{uuid.uuid4().hex}"
    test_val = "test_value_123"

    await client.set(test_key, test_val, ex=60)
    result = await client.get(test_key)
    assert result == test_val

    await client.delete(test_key)
    deleted_result = await client.get(test_key)
    assert deleted_result is None
