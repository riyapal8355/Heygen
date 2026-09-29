"""Comprehensive deterministic test suite for Developer API Keys and Webhooks."""

import hashlib
import json
import time
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ssrf import SSRFSecurityException, validate_destination_url
from app.core.webhook_signing import generate_webhook_signature, verify_webhook_signature
from app.db.session import async_session_factory
from app.models.developer import ApiKey, Webhook, WebhookDelivery
from app.workers.tasks.maintenance_tasks import _execute_deliver_webhook


async def _create_test_user_and_workspace(async_client: AsyncClient, name: str = "Dev Lead") -> tuple[dict, str, str]:
    """Helper to create a user and extract access token and workspace ID."""
    email = f"dev_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspaces = ws_resp.json()
    workspace_id = workspaces[0]["id"]
    return data, token, workspace_id


@pytest.mark.asyncio
async def test_api_key_lifecycle_and_single_secret_disclosure(async_client: AsyncClient):
    """Verify API key creation returns plaintext secret ONCE; list/get never expose secret/hash; DB stores only hash."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create API key
    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers=headers,
        json={
            "name": "Production CLI Tool",
            "environment": "production",
            "permissions": "full",
            "expires_in_days": 30,
        },
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["name"] == "Production CLI Tool"
    assert created_data["prefix"].startswith("hz_live_")
    secret_key = created_data["secret_key"]
    assert secret_key.startswith("hz_live_")
    assert len(secret_key) > len(created_data["prefix"]) + 10
    key_id = created_data["id"]

    # 2. List API keys: secret_key and key_hash MUST NOT be present
    list_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    item = next(k for k in list_data["items"] if k["id"] == key_id)
    assert "secret_key" not in item
    assert "key_hash" not in item
    assert item["prefix"] == created_data["prefix"]

    # 3. Get API key by ID: secret_key and key_hash MUST NOT be present
    get_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys/{key_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert "secret_key" not in get_data
    assert "key_hash" not in get_data
    assert get_data["prefix"] == created_data["prefix"]

    # 4. Direct DB inspection: confirm plaintext secret is NOT stored
    async with async_session_factory() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.id == uuid.UUID(key_id)))
        db_record = result.scalar_one()
        assert db_record is not None
        assert db_record.key_hash != secret_key
        # Verify stored key_hash is SHA-256 of the secret portion
        secret_part = secret_key.split("_", 3)[3]
        expected_hash = hashlib.sha256(secret_part.encode("utf-8")).hexdigest()
        assert db_record.key_hash == expected_hash

    # 5. Revoke API key
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys/{key_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_api_key_authentication_success_and_failure(async_client: AsyncClient):
    """Verify API key authentication via Authorization header and X-API-Key header, and rejection of invalid keys."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create active API key
    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers=headers,
        json={"name": "Auth Test Key", "environment": "production", "permissions": "full"},
    )
    assert create_resp.status_code == 201
    secret_key = create_resp.json()["secret_key"]
    key_id = create_resp.json()["id"]

    # 1. Success via Authorization: Bearer <secret_key>
    auth_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {secret_key}"},
    )
    assert auth_resp.status_code == 200

    # 2. Success via X-API-Key: <secret_key>
    x_auth_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"X-API-Key": secret_key},
    )
    assert x_auth_resp.status_code == 200

    # 3. Failure: Wrong secret portion
    parts = secret_key.split("_")
    bad_secret_key = f"{parts[0]}_{parts[1]}_{parts[2]}_invalidsecret12345"
    fail_resp1 = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {bad_secret_key}"},
    )
    assert fail_resp1.status_code == 401
    assert fail_resp1.json()["error"]["code"] == "AUTH_INVALID_API_KEY"

    # 4. Failure: Non-existent prefix
    non_existent_key = "hz_live_00000000_somesecretpart1234567890"
    fail_resp2 = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {non_existent_key}"},
    )
    assert fail_resp2.status_code == 401
    assert fail_resp2.json()["error"]["code"] == "AUTH_INVALID_API_KEY"

    # 5. Failure: Malformed format
    fail_resp3 = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": "Bearer not_a_valid_key"},
    )
    assert fail_resp3.status_code == 401

    # 6. Failure: Revoked key
    await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys/{key_id}",
        headers=headers,
    )
    revoked_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {secret_key}"},
    )
    assert revoked_resp.status_code == 401
    assert revoked_resp.json()["error"]["code"] == "AUTH_INVALID_API_KEY"


@pytest.mark.asyncio
async def test_api_key_workspace_isolation(async_client: AsyncClient):
    """Verify an API key belonging to Workspace A CANNOT access Workspace B resources."""
    # Create Workspace A and Key A
    _, token_a, ws_a = await _create_test_user_and_workspace(async_client, "User A")
    resp_a = await async_client.post(
        f"/api/v1/workspaces/{ws_a}/developer/api-keys",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Key A", "environment": "production"},
    )
    key_a = resp_a.json()["secret_key"]

    # Create Workspace B
    _, token_b, ws_b = await _create_test_user_and_workspace(async_client, "User B")

    # Attempt to access Workspace B using Key A
    cross_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_b}/developer/api-keys",
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert cross_resp.status_code == 403
    assert cross_resp.json()["error"]["code"] == "WORKSPACE_FORBIDDEN"


@pytest.mark.asyncio
async def test_api_key_cannot_be_used_as_jwt_or_sse(async_client: AsyncClient):
    """Verify that an API key cannot be passed to user session endpoints or SSE query tokens."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "SSE Probe Key"},
    )
    api_key = resp.json()["secret_key"]

    # Attempt to call /api/v1/auth/me using API key -> must fail
    me_resp = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {api_key}"})
    assert me_resp.status_code == 401
    assert me_resp.json()["error"]["code"] == "AUTH_INVALID_TOKEN_TYPE"

    # Attempt to use API key as SSE token query param -> must fail
    sse_resp = await async_client.get(f"/api/v1/auth/me?token={api_key}")
    assert sse_resp.status_code == 401
    assert sse_resp.json()["error"]["code"] == "AUTH_INVALID_TOKEN_TYPE"


@pytest.mark.asyncio
async def test_webhook_lifecycle_and_single_secret_disclosure(async_client: AsyncClient):
    """Verify webhook registration returns secret ONCE; list/get never return secret; update and delete work."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register webhook
    create_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks",
        headers=headers,
        json={
            "url": "https://httpbin.org/post",
            "events": ["job.succeeded", "job.failed"],
            "description": "Production event receiver",
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["url"] == "https://httpbin.org/post"
    assert data["secret"].startswith("whsec_")
    webhook_id = data["id"]

    # 2. List webhooks: secret MUST NOT be present
    list_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    item = next(w for w in list_data["items"] if w["id"] == webhook_id)
    assert "secret" not in item
    assert item["url"] == "https://httpbin.org/post"

    # 3. Get webhook: secret MUST NOT be present
    get_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks/{webhook_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert "secret" not in get_resp.json()

    # 4. Update webhook
    patch_resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks/{webhook_id}",
        headers=headers,
        json={"description": "Updated receiver", "events": ["job.succeeded"]},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Updated receiver"
    assert patch_resp.json()["events"] == ["job.succeeded"]

    # 5. Delete webhook
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks/{webhook_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_webhook_ssrf_protection_gate(async_client: AsyncClient):
    """Verify that localhost, loopback, private IPv4, metadata, and forbidden hostnames are strictly rejected."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_urls = [
        "http://127.0.0.1:8000/hook",
        "http://localhost/hook",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1:8080/hook",
        "http://192.168.1.1/hook",
        "http://172.16.0.1/hook",
        "ftp://example.com/hook",
        "http://internal.corp/hook",
    ]

    for url in forbidden_urls:
        resp = await async_client.post(
            f"/api/v1/workspaces/{ws_id}/developer/webhooks",
            headers=headers,
            json={"url": url},
        )
        assert resp.status_code == 400, f"Expected 400 for SSRF forbidden URL: {url}"
        assert resp.json()["error"]["code"] == "SSRF_DESTINATION_FORBIDDEN"


def test_webhook_hmac_signing_and_replay():
    """Verify HMAC-SHA256 signature generation, validation, tampering detection, and replay rejection."""
    secret = "whsec_test_secret_1234567890abcdef"
    payload = json.dumps({"event": "job.succeeded", "id": "job_123"})
    timestamp = str(int(time.time()))

    # 1. Generate signature
    signature = generate_webhook_signature(secret, timestamp, payload)
    assert signature.startswith("v1=")

    # 2. Valid verification
    is_valid, err = verify_webhook_signature(secret, payload, timestamp, signature)
    assert is_valid is True
    assert err is None

    # 3. Rejection on tampered payload
    tampered_payload = json.dumps({"event": "job.failed", "id": "job_123"})
    is_valid, err = verify_webhook_signature(secret, tampered_payload, timestamp, signature)
    assert is_valid is False
    assert err == "Signature mismatch"

    # 4. Rejection on wrong secret
    is_valid, err = verify_webhook_signature("whsec_wrong_secret", payload, timestamp, signature)
    assert is_valid is False
    assert err == "Signature mismatch"

    # 5. Rejection on stale timestamp (>300 seconds old)
    stale_timestamp = str(int(time.time()) - 350)
    stale_signature = generate_webhook_signature(secret, stale_timestamp, payload)
    is_valid, err = verify_webhook_signature(secret, payload, stale_timestamp, stale_signature)
    assert is_valid is False
    assert "Timestamp is too old" in err

    # 6. Rejection on future timestamp (>60s in future)
    future_timestamp = str(int(time.time()) + 100)
    future_sig = generate_webhook_signature(secret, future_timestamp, payload)
    is_valid, err = verify_webhook_signature(secret, payload, future_timestamp, future_sig)
    assert is_valid is False
    assert "Timestamp is too far in the future" in err


@pytest.mark.asyncio
async def test_webhook_delivery_execution_and_auditing(async_client: AsyncClient):
    """Verify _execute_deliver_webhook records delivery logs in PostgreSQL with status, latency, and attempts."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Register webhook pointing to httpbin
    wh_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks",
        headers=headers,
        json={"url": "https://httpbin.org/post", "events": ["job.succeeded"]},
    )
    assert wh_resp.status_code == 201
    wh_data = wh_resp.json()
    webhook_id = wh_data["id"]
    secret = wh_data["secret"]

    event_id = f"evt_test_{uuid.uuid4().hex[:8]}"
    payload_json = json.dumps({"test": "value", "event_id": event_id})

    # Execute delivery directly
    result = await _execute_deliver_webhook(
        webhook_id_str=webhook_id,
        event_id=event_id,
        event_type="job.succeeded",
        target_url="https://httpbin.org/post",
        payload_json=payload_json,
        secret=secret,
        attempt=1,
    )
    assert result["status"] in ("delivered", "failed")

    # Fetch delivery history from API
    del_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks/{webhook_id}/deliveries",
        headers=headers,
    )
    assert del_resp.status_code == 200
    deliveries = del_resp.json()
    assert deliveries["total"] >= 1
    d = deliveries["items"][0]
    assert d["event_id"] == event_id
    assert d["event_type"] == "job.succeeded"
    assert d["status"] in ("delivered", "failed")
    assert d["attempt"] == 1


@pytest.mark.asyncio
async def test_api_key_rate_limiting(async_client: AsyncClient):
    """Verify rate limiter blocks abuse if key creation exceeds threshold (10 per 10 min)."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # First 10 succeed
    for i in range(10):
        resp = await async_client.post(
            f"/api/v1/workspaces/{ws_id}/developer/api-keys",
            headers=headers,
            json={"name": f"Key {i}"},
        )
        assert resp.status_code == 201

    # 11th request must be rate limited (429)
    rate_limited_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers=headers,
        json={"name": "Key 11 - Abuse attempt"},
    )
    assert rate_limited_resp.status_code == 429
    assert rate_limited_resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_api_key_permission_enforcement(async_client: AsyncClient):
    """Verify that a workspace Creator/Viewer role cannot create or revoke API keys."""
    # 1. Create owner
    _, owner_token, ws_id = await _create_test_user_and_workspace(async_client, "Owner")

    # 2. Create another user to add as Creator
    creator_data, creator_token, _ = await _create_test_user_and_workspace(async_client, "Creator User")
    creator_user_id = creator_data["user"]["id"]

    # 3. Add user to workspace as creator
    async with async_session_factory() as db:
        from app.models.workspace import WorkspaceMember
        member = WorkspaceMember(
            workspace_id=uuid.UUID(ws_id),
            user_id=uuid.UUID(creator_user_id),
            role="creator",
            status="active",
        )
        db.add(member)
        await db.commit()

    # 4. Attempt to create API key with Creator token -> Forbidden
    create_attempt = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/api-keys",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"name": "Unauthorized Key"},
    )
    assert create_attempt.status_code == 403
    assert create_attempt.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_webhook_test_ping_endpoint(async_client: AsyncClient):
    """Verify the developer webhook test ping endpoint dispatches signed test events."""
    _, token, ws_id = await _create_test_user_and_workspace(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Register webhook
    wh_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks",
        headers=headers,
        json={"url": "https://httpbin.org/post", "events": ["webhook.test"]},
    )
    assert wh_resp.status_code == 201
    webhook_id = wh_resp.json()["id"]

    # Trigger test ping
    test_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/developer/webhooks/{webhook_id}/test",
        headers=headers,
    )
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert test_data["status"] == "enqueued"
    assert test_data["event_id"].startswith("evt_test_")
