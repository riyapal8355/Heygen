"""Tests for /health and /ready endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness_root(async_client: AsyncClient):
    """Verify GET /health returns HTTP 200 and application metadata."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_liveness_v1(async_client: AsyncClient):
    """Verify GET /api/v1/health returns HTTP 200."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_probe_root(async_client: AsyncClient):
    """Verify GET /ready checks database, redis, and storage dependencies."""
    response = await async_client.get("/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "storage" in data["checks"]


@pytest.mark.asyncio
async def test_readiness_probe_v1(async_client: AsyncClient):
    """Verify GET /api/v1/ready checks dependencies."""
    response = await async_client.get("/api/v1/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "checks" in data
