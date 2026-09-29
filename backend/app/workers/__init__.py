"""Celery workers package."""

from app.workers.celery_app import celery_app, ping

__all__ = ["celery_app", "ping"]
