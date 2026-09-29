"""Production Hardening & Deployment Readiness Test Suite.

Validates:
- Production configuration fail-closed secret validation
- Multi-tenancy cross-workspace isolation
- Asset upload security (dangerous extensions, traversal sanitization, size limits)
- Rate limiting behavior
- Telemetry & metrics snapshot
- Stale job reaper recovery
- Database connection pool settings
- CPU vs GPU queue isolation invariants
"""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.metrics import get_metrics_registry
from app.core.redis import check_rate_limit, reset_rate_limit
from app.db.session import async_engine
from app.main import app
from app.services.asset_service import PROHIBITED_FILE_EXTENSIONS
from app.workers.tasks.maintenance_tasks import _execute_reap_stale_jobs
from app.workers.celery_app import celery_app




# ==============================================================================
# 1. Production Configuration & Secret Validation Tests
# ==============================================================================

def test_production_config_fails_with_dev_secrets():
    """Verify production mode fails startup if insecure dev secrets are present."""
    prod_insecure = Settings(
        APP_ENV="production",
        DEBUG=True,  # Insecure
        JWT_SECRET_KEY="dev_insecure_jwt_secret_key_for_local_testing_only_replace_in_prod",  # Insecure
        DATABASE_URL="postgresql+asyncpg://heyzen:heyzen_dev_password@127.0.0.1:5432/heyzen",  # Insecure
        MINIO_SECRET_KEY="heyzen_dev_password123",  # Insecure
    )
    with pytest.raises(ValueError) as exc_info:
        prod_insecure.validate_production_settings()

    err = str(exc_info.value)
    assert "DEBUG mode must be False in production" in err
    assert "JWT_SECRET_KEY must be a cryptographically strong secret" in err
    assert "DATABASE_URL contains the default insecure development password" in err
    assert "S3/MinIO secret key contains default insecure development credentials" in err


def test_production_config_succeeds_with_strong_secrets():
    """Verify production settings pass validation when all secrets are secure."""
    prod_secure = Settings(
        APP_ENV="production",
        DEBUG=False,
        JWT_SECRET_KEY="a_very_long_cryptographically_secure_random_production_jwt_signing_key_987654321",
        DATABASE_URL="postgresql+asyncpg://heyzen_prod:strong_random_db_password_12345@db.internal:5432/heyzen_prod",
        MINIO_SECRET_KEY="strong_random_s3_secret_key_abcdef123456",
        S3_SECRET_KEY="strong_random_s3_secret_key_abcdef123456",
        CORS_ORIGINS="https://app.heyzen.ai,https://studio.heyzen.ai",
    )
    # Should not raise
    prod_secure.validate_production_settings()



# ==============================================================================
# 2. Multi-Tenancy Cross-Workspace Boundary Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_multitenancy_workspace_isolation():
    """Ensure Workspace A resources cannot be accessed or manipulated by User B."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ts = int(uuid.uuid4().int % 1000000)

        # 1. Create Tenant A
        r_a = await client.post(
            "/api/v1/auth/signup",
            json={"email": f"tenant_a_{ts}@example.com", "password": "SecurePassword123!", "display_name": "Tenant A"},
        )
        assert r_a.status_code == 201
        data_a = r_a.json()
        token_a = data_a["tokens"]["access_token"]
        ws_a_id = data_a["workspace"]["id"]

        # 2. Create Tenant B
        r_b = await client.post(
            "/api/v1/auth/signup",
            json={"email": f"tenant_b_{ts}@example.com", "password": "SecurePassword123!", "display_name": "Tenant B"},
        )
        assert r_b.status_code == 201
        data_b = r_b.json()
        token_b = data_b["tokens"]["access_token"]
        ws_b_id = data_b["workspace"]["id"]

        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Tenant B attempts to create an asset in Tenant A's workspace
        r_asset = await client.post(
            f"/api/v1/workspaces/{ws_a_id}/assets/upload-intents",
            headers=headers_b,
            json={"original_filename": "leak.png", "mime_type": "image/png", "size_bytes": 1024},
        )
        assert r_asset.status_code in (403, 404), f"Cross-workspace asset upload should fail: {r_asset.status_code}"

        # Tenant B attempts to create a project in Tenant A's workspace
        r_proj = await client.post(
            f"/api/v1/workspaces/{ws_a_id}/projects",
            headers=headers_b,
            json={"title": "Hacked Project"},
        )
        assert r_proj.status_code in (403, 404), f"Cross-workspace project creation should fail: {r_proj.status_code}"

        # Tenant B attempts to list Tenant A's assets
        r_list = await client.get(
            f"/api/v1/workspaces/{ws_a_id}/assets",
            headers=headers_b,
        )
        assert r_list.status_code in (403, 404), f"Cross-workspace asset list should fail: {r_list.status_code}"


# ==============================================================================
# 3. Asset Upload Security & Sanitization Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_upload_security_prohibited_extensions():
    """Verify that dangerous executables and scripts are rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ts = int(uuid.uuid4().int % 1000000)
        r_auth = await client.post(
            "/api/v1/auth/signup",
            json={"email": f"sec_user_{ts}@example.com", "password": "SecurePassword123!", "display_name": "Sec User"},
        )
        data = r_auth.json()
        token = data["tokens"]["access_token"]
        ws_id = data["workspace"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test prohibited extensions
        dangerous_names = ["trojan.exe", "script.sh", "backdoor.php", "exploit.bat", "run.ps1"]
        for bad_name in dangerous_names:
            r_bad = await client.post(
                f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
                headers=headers,
                json={"original_filename": bad_name, "mime_type": "application/octet-stream", "size_bytes": 1024},
            )
            assert r_bad.status_code == 409
            assert "ASSET_DANGEROUS_EXTENSION" in r_bad.text


@pytest.mark.asyncio
async def test_upload_security_path_traversal_sanitization():
    """Verify path traversal filenames are sanitized and stripped of relative components."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ts = int(uuid.uuid4().int % 1000000)
        r_auth = await client.post(
            "/api/v1/auth/signup",
            json={"email": f"trav_user_{ts}@example.com", "password": "SecurePassword123!", "display_name": "Trav User"},
        )
        data = r_auth.json()
        token = data["tokens"]["access_token"]
        ws_id = data["workspace"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Traversal attempt
        r_trav = await client.post(
            f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
            headers=headers,
            json={"original_filename": "../../../etc/passwd.png", "mime_type": "image/png", "size_bytes": 1024},
        )
        assert r_trav.status_code == 201
        key = r_trav.json()["storage_key"]
        assert ".." not in key
        assert key.endswith("/passwd.png")


@pytest.mark.asyncio
async def test_upload_security_oversized_file():
    """Verify files larger than 500MB are blocked at upload-intent creation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ts = int(uuid.uuid4().int % 1000000)
        r_auth = await client.post(
            "/api/v1/auth/signup",
            json={"email": f"size_user_{ts}@example.com", "password": "SecurePassword123!", "display_name": "Size User"},
        )
        data = r_auth.json()
        token = data["tokens"]["access_token"]
        ws_id = data["workspace"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 550MB file
        r_big = await client.post(
            f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
            headers=headers,
            json={"original_filename": "huge_movie.mp4", "mime_type": "video/mp4", "size_bytes": 550 * 1024 * 1024},
        )
        assert r_big.status_code == 409
        assert "ASSET_SIZE_EXCEEDED" in r_big.text


# ==============================================================================
# 4. Rate Limiting Behavior Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_redis_rate_limiting_enforcement():
    """Verify check_rate_limit enforces sliding-window threshold."""
    test_key = f"test_rate_limit:{uuid.uuid4()}"
    limit = 3
    window = 10

    try:
        # First 3 should pass
        assert await check_rate_limit(test_key, max_requests=limit, window_seconds=window) is True
        assert await check_rate_limit(test_key, max_requests=limit, window_seconds=window) is True
        assert await check_rate_limit(test_key, max_requests=limit, window_seconds=window) is True

        # 4th request must be rate-limited
        assert await check_rate_limit(test_key, max_requests=limit, window_seconds=window) is False
    finally:
        await reset_rate_limit(test_key)


# ==============================================================================
# 5. Metrics & Telemetry Snapshot Tests
# ==============================================================================

def test_metrics_registry_snapshot():
    """Verify MetricsRegistry accumulates request and job telemetry."""
    registry = get_metrics_registry()

    # Record sample API requests
    registry.record_api_request("GET", "/health", 200, 5.2)
    registry.record_api_request("POST", "/api/v1/projects", 201, 24.8)
    registry.record_api_request("GET", "/missing", 404, 2.1)

    # Record job transitions
    registry.record_job_submitted("video_render")
    registry.record_job_finished("video_render", "succeeded", duration_seconds=12.5)

    # Record subsystem errors
    registry.record_error("storage")

    snapshot = registry.get_snapshot()
    assert snapshot["api"]["requests_total"] >= 3
    assert snapshot["api"]["errors_total"] >= 1
    assert snapshot["jobs"]["submitted_total"] >= 1
    assert snapshot["jobs"]["succeeded_total"] >= 1
    assert snapshot["subsystems"]["storage_failures"] >= 1


# ==============================================================================
# 6. Database Connection Pool Settings
# ==============================================================================

def test_database_connection_pool_configuration():
    """Verify async database engine pool is configured with production parameters."""
    pool = async_engine.pool
    assert pool.size() >= 1
    assert pool._max_overflow >= 0
    assert pool._recycle >= 60


# ==============================================================================
# 7. Celery Queue & Worker Routing Invariants
# ==============================================================================

def test_celery_queue_isolation_invariants():
    """Verify task routing strictly isolates CPU media from GPU AI queues."""
    routes = celery_app.conf.task_routes or {}

    # Confirm gpu_ai task routing
    assert routes.get("heyzen.tasks.ai.*") == {"queue": "gpu_ai", "routing_key": "gpu_ai"}

    # Confirm cpu_media task routing
    assert routes.get("heyzen.tasks.media.*") == {"queue": "cpu_media", "routing_key": "cpu_media"}
    assert routes.get("heyzen.tasks.ai.generate_project") == {"queue": "cpu_media", "routing_key": "cpu_media"}
    assert routes.get("heyzen.tasks.ai.extract_matte") == {"queue": "cpu_media", "routing_key": "cpu_media"}

    # Confirm maintenance queue
    assert routes.get("heyzen.tasks.maintenance.*") == {"queue": "maintenance", "routing_key": "maintenance"}


# ==============================================================================
# 8. Stale Job Reaper Execution
# ==============================================================================

from app.workers.tasks.maintenance_tasks import _execute_reap_stale_jobs

@pytest.mark.asyncio
async def test_stale_job_reaper_safe_execution():
    """Verify stale job recovery task executes safely without raising exceptions."""
    result = await _execute_reap_stale_jobs(timeout_minutes=120)
    assert isinstance(result, dict)
    assert "reaped_jobs" in result
    assert result["reaped_jobs"] >= 0

