"""Tests for Celery application configuration and ping task."""

from app.workers.celery_app import celery_app, ping


def test_celery_broker_config():
    """Verify Celery app broker URL is configured."""
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.result_backend.startswith("redis://")


def test_celery_ping_task():
    """Verify ping task returns expected structure and pong status."""
    result = ping()
    assert result is not None
    assert result["status"] == "pong"
    assert "timestamp" in result
    assert "app" in result
