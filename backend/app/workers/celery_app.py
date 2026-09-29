"""Celery application configuration, multi-queue topology, and foundational worker tasks."""

from datetime import datetime, timezone
from typing import Any, Dict
from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

# Initialize Celery app instance pointing to Redis broker and backend
celery_app = Celery(
    "heyzen_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Dedicated direct exchange for HeyZen task routing
default_exchange = Exchange("heyzen", type="direct")

# Multi-Queue Topology configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry=False,
    broker_connection_retry_on_startup=False,
    result_backend_transport_options={"retry_policy": {"max_retries": 0}},
    task_default_queue="cpu_media",
    task_queues=(
        Queue("cpu_media", default_exchange, routing_key="cpu_media"),
        Queue("gpu_ai", default_exchange, routing_key="gpu_ai"),
        Queue("maintenance", default_exchange, routing_key="maintenance"),
    ),
    task_routes={
        "heyzen.tasks.media.*": {"queue": "cpu_media", "routing_key": "cpu_media"},
        "heyzen.tasks.ai.generate_project": {"queue": "cpu_media", "routing_key": "cpu_media"},
        "heyzen.tasks.ai.translate_project": {"queue": "cpu_media", "routing_key": "cpu_media"},
        "heyzen.tasks.ai.extract_matte": {"queue": "cpu_media", "routing_key": "cpu_media"},
        "heyzen.tasks.ai.*": {"queue": "gpu_ai", "routing_key": "gpu_ai"},
        "heyzen.tasks.maintenance.*": {"queue": "maintenance", "routing_key": "maintenance"},
        "heyzen.ping": {"queue": "cpu_media", "routing_key": "cpu_media"},
    },
)


@celery_app.task(name="heyzen.ping")
def ping() -> Dict[str, Any]:
    """Foundational test task to verify Celery broker and worker execution."""
    return {
        "status": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": settings.APP_NAME,
    }


# Register tasks modules for worker discovery
import app.workers.tasks.ai_tasks  # noqa: F401, E402
import app.workers.tasks.maintenance_tasks  # noqa: F401, E402
import app.workers.tasks.media_tasks  # noqa: F401, E402
