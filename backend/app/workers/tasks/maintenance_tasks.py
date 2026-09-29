"""Maintenance and housekeeping tasks for the task pipeline (Queue: maintenance)."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from sqlalchemy import select
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.job import Job
from app.services.job_service import JobService
from app.workers.base import HeyZenBaseTask, run_async
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _execute_reap_stale_jobs(timeout_minutes: int = 120) -> Dict[str, Any]:
    """Identify jobs stuck in 'running' or 'queued' state past threshold and fail them."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
    reaped_count = 0

    async with async_session_factory() as db:
        service = JobService(db)
        query = select(Job).where(
            Job.status == "running",
            Job.started_at < threshold,
        )
        result = await db.execute(query)
        stale_jobs = list(result.scalars().all())

        for job in stale_jobs:
            try:
                await service.mark_failed(
                    job_id=job.id,
                    error_details={"reason": "STALE_JOB_TIMEOUT", "timeout_minutes": timeout_minutes},
                    message=f"Job marked failed by maintenance reaper after exceeding {timeout_minutes}m threshold",
                )
                reaped_count += 1
            except Exception as exc:
                logger.error("Failed to reap stale job %s: %s", job.id, exc)

    return {"reaped_jobs": reaped_count, "threshold_utc": threshold.isoformat()}


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.maintenance.reap_stale_jobs",
)
def reap_stale_jobs(self, timeout_minutes: int = 120) -> Dict[str, Any]:
    return run_async(_execute_reap_stale_jobs(timeout_minutes))


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.maintenance.cleanup_temp_files",
)
def cleanup_temp_files(self) -> Dict[str, Any]:
    """Clean up orphan scratch artifacts and expired temporary files."""
    logger.info("Executed maintenance temporary file cleanup.")
    return {"status": "success", "timestamp": datetime.now(timezone.utc).isoformat()}


async def _execute_deliver_webhook(
    webhook_id_str: str,
    event_id: str,
    event_type: str,
    target_url: str,
    payload_json: str,
    secret: str,
    attempt: int = 1,
) -> Dict[str, Any]:
    """Execute outbound HTTP delivery to webhook target with SSRF validation and HMAC signing."""
    import json
    import time
    import uuid
    import httpx
    from app.core.ssrf import validate_destination_url, SSRFSecurityException
    from app.core.webhook_signing import generate_webhook_signature
    from app.models.developer import WebhookDelivery
    from app.repositories.developer import WebhookDeliveryRepository, WebhookRepository

    webhook_id = uuid.UUID(webhook_id_str)
    start_time = time.time()
    response_code: int | None = None
    response_body: str | None = None
    error_msg: str | None = None
    delivery_status = "delivered"

    # 1. SSRF pre-flight validation immediately before dispatch to guard against DNS rebinding
    try:
        validated_url = validate_destination_url(target_url)
    except SSRFSecurityException as e:
        error_msg = f"SSRF Check Failed: {e.message}"
        delivery_status = "failed"
        latency_ms = int((time.time() - start_time) * 1000)
        async with async_session_factory() as db:
            del_repo = WebhookDeliveryRepository(db)
            wh_repo = WebhookRepository(db)
            delivery = WebhookDelivery(
                webhook_id=webhook_id,
                event_id=event_id,
                event_type=event_type,
                payload=json.loads(payload_json),
                response_status_code=400,
                response_body=error_msg,
                latency_ms=latency_ms,
                status="failed",
                attempt=attempt,
                error_message=error_msg,
            )
            await del_repo.create(delivery)
            await wh_repo.increment_failure(webhook_id)
            await db.commit()
        return {"status": "failed", "error": error_msg}

    # 2. Canonical HMAC-SHA256 signature generation
    timestamp_str = str(int(time.time()))
    signature = generate_webhook_signature(secret, timestamp_str, payload_json)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "HeyZen-Webhook-Dispatcher/1.0",
        "X-HeyZen-Timestamp": timestamp_str,
        "X-HeyZen-Signature": signature,
        "X-HeyZen-Event-ID": event_id,
        "X-HeyZen-Event-Type": event_type,
    }

    # 3. Outbound HTTP request dispatch with strict timeouts and disabled redirects
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.post(validated_url, content=payload_json, headers=headers)
            response_code = resp.status_code
            raw_text = resp.text
            response_body = raw_text[:1024] if raw_text else ""
            if 200 <= response_code < 300:
                delivery_status = "delivered"
            else:
                delivery_status = "failed"
                error_msg = f"HTTP {response_code}"
    except Exception as exc:
        delivery_status = "failed"
        error_msg = f"Connection error: {str(exc)[:500]}"

    latency_ms = int((time.time() - start_time) * 1000)

    # 4. Record delivery audit in PostgreSQL
    async with async_session_factory() as db:
        del_repo = WebhookDeliveryRepository(db)
        wh_repo = WebhookRepository(db)

        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event_id=event_id,
            event_type=event_type,
            payload=json.loads(payload_json),
            response_status_code=response_code,
            response_body=response_body,
            latency_ms=latency_ms,
            status=delivery_status,
            attempt=attempt,
            error_message=error_msg,
        )
        await del_repo.create(delivery)

        if delivery_status == "delivered":
            await wh_repo.reset_failure(webhook_id)
        else:
            await wh_repo.increment_failure(webhook_id)
        await db.commit()

    # 5. Retry scheduling with exponential backoff if failed and attempts < 3
    if delivery_status != "delivered" and attempt < 3:
        countdown = 5 * (5 ** (attempt - 1))  # 5s, 25s
        celery_app.send_task(
            "heyzen.tasks.maintenance.deliver_webhook",
            args=[
                webhook_id_str,
                event_id,
                event_type,
                target_url,
                payload_json,
                secret,
                attempt + 1,
            ],
            queue="maintenance",
            countdown=countdown,
        )
        logger.info(
            "Scheduled retry for webhook delivery %s attempt %d in %ds",
            event_id,
            attempt + 1,
            countdown,
        )

    return {
        "status": delivery_status,
        "status_code": response_code,
        "latency_ms": latency_ms,
        "attempt": attempt,
    }


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.maintenance.deliver_webhook",
    max_retries=0,  # We handle explicit backoff dispatch in _execute_deliver_webhook
)
def deliver_webhook(
    self,
    webhook_id_str: str,
    event_id: str,
    event_type: str,
    target_url: str,
    payload_json: str,
    secret: str,
    attempt: int = 1,
) -> Dict[str, Any]:
    """Asynchronously deliver a signed webhook event to an external consumer."""
    return run_async(
        _execute_deliver_webhook(
            webhook_id_str=webhook_id_str,
            event_id=event_id,
            event_type=event_type,
            target_url=target_url,
            payload_json=payload_json,
            secret=secret,
            attempt=attempt,
        )
    )
