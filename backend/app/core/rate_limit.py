"""Reusable Redis-backed Rate Limiter dependency for FastAPI endpoints."""

from typing import Callable, Optional
from fastapi import Request, Response

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededException
from app.core.redis import check_rate_limit


class RateLimiter:
    """FastAPI dependency for endpoint-level rate limiting backed by Redis."""

    def __init__(
        self,
        key_prefix: str,
        max_requests: Optional[int] = None,
        window_seconds: int = 60,
    ):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request, response: Response) -> None:
        settings = get_settings()

        # Resolve limit
        limit = self.max_requests
        if limit is None:
            if "auth" in self.key_prefix:
                limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
            elif "ai_job" in self.key_prefix:
                limit = settings.RATE_LIMIT_AI_JOB_PER_MINUTE
            elif "upload" in self.key_prefix:
                limit = settings.RATE_LIMIT_UPLOAD_PER_MINUTE
            else:
                limit = settings.RATE_LIMIT_API_PER_MINUTE

        # Determine client identifier
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        user_id = getattr(request.state, "user_id", None)
        identifier = f"user:{user_id}" if user_id else f"ip:{client_ip}"
        rate_key = f"rate_limit:{self.key_prefix}:{identifier}"

        allowed = await check_rate_limit(rate_key, max_requests=limit, window_seconds=self.window_seconds)
        if not allowed:
            response.headers["Retry-After"] = str(self.window_seconds)
            raise RateLimitExceededException(
                message=f"Rate limit of {limit} requests per {self.window_seconds}s exceeded.",
                code="RATE_LIMIT_EXCEEDED",
                retry_after=self.window_seconds,
            )
