"""Integration tests for AI Runtime Health endpoints (/health/ai, /api/v1/health/ai)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_health_endpoint_root(async_client: AsyncClient):
    """Verify GET /health/ai returns 200 with runtime and hardware telemetry."""
    response = await async_client.get("/health/ai")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "hardware" in data
    assert "cpu_model" in data["hardware"]
    assert "cpu_cores" in data["hardware"]
    assert "cuda_available" in data["hardware"]

    # Runtimes section
    assert "runtimes" in data
    assert "cpu" in data["runtimes"]
    assert "gpu" in data["runtimes"]
    assert data["runtimes"]["cpu"] in ("healthy", "degraded")

    # Capabilities section
    assert "capabilities" in data
    for cap in ("tts", "asr", "translation", "image", "avatar", "video", "llm"):
        assert cap in data["capabilities"]
        assert "status" in data["capabilities"][cap]
        assert "runtime_id" in data["capabilities"][cap]
        assert "active_model" in data["capabilities"][cap]


@pytest.mark.asyncio
async def test_ai_health_endpoint_v1(async_client: AsyncClient):
    """Verify GET /api/v1/health/ai returns HTTP 200 with identical structure."""
    response = await async_client.get("/api/v1/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert "runtimes" in data
    assert "hardware" in data
    assert "capabilities" in data


@pytest.mark.asyncio
async def test_core_health_and_readiness_remain_functional(async_client: AsyncClient):
    """Verify existing /health and /ready probes continue working without regression."""
    r_health = await async_client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_ready = await async_client.get("/ready")
    assert r_ready.status_code in (200, 503)
    assert "checks" in r_ready.json()
