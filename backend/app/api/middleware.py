"""API Middleware for correlation request IDs and timing."""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_ctx, get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensures every HTTP request has a unique Request ID for distributed tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check incoming X-Request-ID header or generate a new UUID
        req_id = request.headers.get("X-Request-ID")
        if not req_id or len(req_id) > 128:
            req_id = str(uuid.uuid4())

        # Store in request state and contextvar for logging
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)

        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            process_time = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            return response
        finally:
            process_time = (time.perf_counter() - start_time) * 1000.0
            try:
                from app.core.metrics import get_metrics_registry
                get_metrics_registry().record_api_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=process_time,
                )
            except Exception:
                pass
            request_id_ctx.reset(token)

