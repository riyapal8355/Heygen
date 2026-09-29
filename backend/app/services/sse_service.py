"""Server-Sent Events (SSE) streaming service for real-time Job progress."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.repositories.job import JobRepository

logger = get_logger(__name__)


async def stream_job_events(
    job_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Yield Server-Sent Events (SSE) formatted text chunks for a given job.

    Listens on Redis Pub/Sub channel 'job:events:{job_id}' until a terminal state
    (succeeded, failed, cancelled) is reached or client disconnects.
    """
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id(job_id, workspace_id)
    if not job:
        raise NotFoundException(
            code="JOB_NOT_FOUND",
            message=f"Job '{job_id}' not found in this workspace.",
        )

    # 1. Send initial state event immediately to sync client
    initial_event = {
        "job_id": str(job.id),
        "status": job.status,
        "progress_percent": job.progress_percent,
        "stage": job.stage,
        "message": job.stage_message,
        "result": job.result,
        "error_details": job.error_details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"data: {json.dumps(initial_event, default=str)}\n\n"

    # If job is already in terminal state, no need to subscribe to pubsub
    if job.status in ("succeeded", "failed", "cancelled"):
        return

    # 2. Subscribe to Redis pub/sub channel for dynamic live updates
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    channel = f"job:events:{job_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            # Poll with timeout to allow keepalive pings and cooperative cancellation
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                if data:
                    yield f"data: {data}\n\n"
                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in ("succeeded", "failed", "cancelled"):
                            break
                    except Exception:
                        pass
            else:
                # SSE comment keep-alive heartbeat to prevent intermediate proxy timeout
                yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.debug("Client disconnected SSE stream for job %s", job_id)
        raise
    except Exception as exc:
        logger.warning("Error in SSE event stream for job %s: %s", job_id, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass
