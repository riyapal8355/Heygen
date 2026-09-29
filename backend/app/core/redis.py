"""Redis client connection pool and async client utilities."""

import asyncio
from typing import Optional
from redis.asyncio import ConnectionPool, Redis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initialize async Redis connection pool."""
    global _redis_pool, _redis_client
    settings = get_settings()
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
    if _redis_pool is not None:
        try:
            await _redis_pool.disconnect()
        except Exception:
            pass
        _redis_pool = None

    _redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=50,
        decode_responses=True,
    )
    _redis_client = Redis(connection_pool=_redis_pool)
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool gracefully."""
    global _redis_pool, _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
    if _redis_pool is not None:
        try:
            await _redis_pool.disconnect()
        except Exception:
            pass
        _redis_pool = None


async def get_redis() -> Redis:
    """Dependency / accessor to get active Redis client."""
    global _redis_client
    if _redis_client is None:
        return await init_redis()
    return _redis_client


async def ping_redis() -> bool:
    """Check Redis health by issuing PING command."""
    try:
        client = await get_redis()
        response = await client.ping()
        return bool(response)
    except Exception as e:
        logger.error("Redis ping check failed: %s", e)
        # Attempt recovery on next call
        await close_redis()
        return False


async def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Sliding-window / fixed-window rate limiter using Redis atomic INCR and EXPIRE.

    Returns True if request is allowed, False if rate limited.
    """
    try:
        client = await get_redis()
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window_seconds)
        return current <= max_requests
    except Exception as e:
        logger.warning("Rate limiter bypass due to Redis error: %s", e)
        return True


async def reset_rate_limit(key: str) -> None:
    """Clear rate limit counter after successful action."""
    try:
        client = await get_redis()
        await client.delete(key)
    except Exception as e:
        logger.warning("Failed to reset rate limit key %s: %s", key, e)

