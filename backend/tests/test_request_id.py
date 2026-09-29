"""Tests for X-Request-ID propagation and error response formats."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_generated_if_absent(async_client: AsyncClient):
    """Verify X-Request-ID is generated and returned if client does not provide one."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) > 0
    assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_request_id_propagated_if_supplied(async_client: AsyncClient):
    """Verify client-supplied X-Request-ID is preserved and reflected in response."""
    custom_id = "client-trace-id-abc-123"
    response = await async_client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_error_response_format(async_client: AsyncClient):
    """Verify 404 error returns structured error envelope containing request_id."""
    response = await async_client.get("/non-existent-route-for-testing")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
    assert data["error"]["request_id"] == response.headers.get("X-Request-ID")
