# Phase 18 — Developer API Keys & Webhooks Implementation Report

## 1. Implementation Summary

Phase 18 implements the complete backend subsystem for **Developer API Keys** and **Webhooks** in HeyZen, strictly preserving:
- Existing Next.js frontend, layout, components, and design system.
- Zero additions or changes to `package.json`, `package-lock.json`, and `public/**`.
- Existing JWT/session browser authentication and SSE query tokens.
- Complete workspace tenancy isolation and RBAC permission models.
- PostgreSQL as durable source of truth, Redis as caching/rate-limiting infrastructure, Celery as async worker queue, and MinIO as object storage.

---

## 2. API Key Format & Storage

### 2.1 Format
Keys use the standardized conceptual format:
`hz_<environment>_<public_identifier>_<secret>`

Example:
`hz_live_a1b2c3d4_8X9K2mL0pQrStUvWxYz1234567890abcdef`

- `hz`: System namespace indicator.
- `<environment>`: `live` (production) or `test` (sandbox).
- `<public_identifier>`: 8-character random hexadecimal string (`secrets.token_hex(4)`). Stored as `prefix` for indexed lookup, display, and audit logging.
- `<secret>`: 32-byte cryptographically secure random token (`secrets.token_urlsafe(32)`).

### 2.2 Storage & Hashing
- **Plaintext Secret:** Disclosed **strictly once** in the creation API response (`POST /api/v1/workspaces/{workspace_id}/developer/api-keys`).
- **Persistence:** Only the SHA-256 hash (`hashlib.sha256(secret.encode()).hexdigest()`) and public prefix are stored in PostgreSQL. Plaintext secrets are **NEVER** persisted or logged.
- **Constant-Time Verification:** Key matching uses `hmac.compare_digest` to prevent timing attacks, and dummy comparisons execute even on non-existent prefixes to eliminate side-channels.

---

## 3. Authentication Flow

API Key authentication is integrated seamlessly into FastAPI dependency injection:
1. **Extraction:** Accepts `Authorization: Bearer hz_...` or `X-API-Key: hz_...`.
2. **Key Prefix Routing:** Separates JWT tokens from Developer API Keys by detecting the `hz_` namespace.
3. **Lookup & Verification:** Locates candidate key by `prefix` in `api_keys` table and performs constant-time SHA-256 hash comparison.
4. **Lifecycle & Expiration Checks:** Confirms `status == 'active'` and `expires_at is None or expires_at > now()`.
5. **Workspace Boundary Isolation:** Resolves owning workspace (`status == 'active'`) and verifies route `workspace_id` matching. Rejects cross-workspace access with 403 Forbidden.
6. **Telemetry & Audit:** Asynchronously updates `last_used_at` timestamp.
7. **Generic Error Responses:** Never leaks whether an identifier exists, whether a secret was wrong, or whether a key was revoked. Always returns generic structured 401 `AUTH_INVALID_API_KEY`.

---

## 4. Permission Model & RBAC

Developer management capabilities are governed by existing workspace roles:
- **`api_key.create` / `api_key.revoke`:** Permitted for `Owner` and `Admin`. Denied for `Creator` and `Viewer` (HTTP 403 `INSUFFICIENT_PERMISSIONS`).
- **`api_key.read`:** Permitted for `Owner` and `Admin`.
- **`webhook.create` / `webhook.manage`:** Permitted for `Owner` and `Admin`.
- **`webhook.read`:** Permitted for `Owner` and `Admin`.
- **API Key Service Principal Execution:** API keys with `full` permission execute workspace operations as Admin service principals; keys with `read_only` permission execute as Viewer service principals.

---

## 5. Webhook Registration & SSRF Protection

### 5.1 Registration
- Endpoints: `POST /api/v1/workspaces/{workspace_id}/developer/webhooks`
- Parameters: `url`, `events` (e.g. `["job.succeeded", "job.failed"]`), `description`.
- Signing Secret: Generated cryptographically (`whsec_<random32>`) and returned strictly once upon registration.

### 5.2 Server-Side Request Forgery (SSRF) Protection Gate
Before storing or dispatching to any destination URL, the URL passes strict multi-layer SSRF gates ([backend/app/core/ssrf.py](file:///d:/HeyGen/video-ai-tools/backend/app/core/ssrf.py)):
1. **Scheme Validation:** Only `http://` and `https://` schemes are permitted.
2. **Hostname Blocklist:** Blocks `localhost`, `metadata.google.internal`, `metadata`, `instance-data`, and suffixes (`.localhost`, `.local`, `.internal`, `.corp`, `.lan`).
3. **Synchronous DNS Pre-Resolution:** Resolves hostname via `socket.getaddrinfo` and checks **all** resolved IPv4 and IPv6 addresses against comprehensive blocked network ranges:
   - Loopback (`127.0.0.0/8`, `::1`)
   - Private IPv4 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   - Link-local & Cloud metadata (`169.254.0.0/16`, `fe80::/10`)
   - Carrier-grade NAT (`100.64.0.0/10`)
   - Multicast & Broadcast (`224.0.0.0/4`, `ff00::/8`, `255.255.255.255/32`)
   - Unique Local IPv6 (`fc00::/7`)
4. **No-Redirect Policy:** Outbound HTTP client executes with `follow_redirects=False` to prevent redirect-based SSRF or DNS rebinding bypasses.

---

## 6. Webhook Signing & Replay Protection

### 6.1 HMAC-SHA256 Signature Specification
Signatures are computed over the exact canonical raw payload string and epoch timestamp:
- **Canonical Message:** `<timestamp>.<raw_payload_json>`
- **Algorithm:** `HMAC-SHA256(secret, canonical_message)`
- **Header Value:** `X-HeyZen-Signature: v1=<hexdigest>`

Dispatched Headers:
- `Content-Type: application/json`
- `User-Agent: HeyZen-Webhook-Dispatcher/1.0`
- `X-HeyZen-Timestamp: <utc_epoch_seconds>`
- `X-HeyZen-Signature: v1=<hmac_sha256_hex>`
- `X-HeyZen-Event-ID: <event_uuid>`
- `X-HeyZen-Event-Type: <event_name>`

### 6.2 Replay & Tampering Protection
- Consumers verify that $|t_{\text{current}} - t_{\text{timestamp}}| \le 300\text{ seconds}$ (5-minute replay tolerance window).
- Rejects timestamps skewed $>60\text{ seconds}$ into the future.
- Uses `hmac.compare_digest` for constant-time cryptographic verification.

---

## 7. Asynchronous Celery Delivery & Idempotency

1. **Queue:** Routes to Celery `maintenance` queue (`heyzen.tasks.maintenance.deliver_webhook`).
2. **Non-Blocking:** Webhook calls are never executed inside FastAPI request-response handlers.
3. **Bounded Retries & Exponential Backoff:**
   - Maximum 3 delivery attempts.
   - Retry delays: 5 seconds, 25 seconds.
4. **Timeout:** Strict 10.0-second connection and read timeout.
5. **Idempotency:** Stable `event_id` is preserved across all retry attempts for downstream consumer deduplication.
6. **Failure Breaker:** Webhooks increment `failure_count` on failed attempts. If consecutive failures reach 5, the webhook status is automatically transitioned to `disabled`.
7. **Delivery Auditing:** Every attempt is durably recorded in `webhook_deliveries` with HTTP status code, sanitized response snippet (max 1024 chars), roundtrip latency ms, and attempt number.

---

## 8. Database Schema & Migration Decision

During the read-only audit, all 21 tables were inspected. No existing table could safely persist developer credentials without violating domain boundaries, breaking RBAC, or risking data loss.
With user authorization, migration `0006_api_keys_and_webhooks.py` was created and applied, cleanly advancing Alembic:
`0005_jobs_task_pipeline` $\to$ `0006_api_keys_and_webhooks (head)`.

### Summary of New Tables:
1. `api_keys`: Scoped to `workspace_id`, stores prefix, SHA-256 hash, environment, permissions, status, and usage timestamps.
2. `webhooks`: Scoped to `workspace_id`, stores destination URL, signing secret, subscribed events JSONB, failure count, and status.
3. `webhook_deliveries`: Scoped to `webhook_id`, stores event ID, payload JSONB, response status, sanitized response body, latency ms, attempt count, and status.

---

## 9. Verification & Test Summary

| Test Suite | Commands | Result |
|---|---|---|
| Phase 18 Targeted Tests | `pytest tests/test_developer_api_and_webhooks.py` | **11 passed in 9.61s** |
| Security Regression | `pytest tests/test_security.py` | **5 passed in 0.55s** |
| Phase 11 Frontend Integration | `pytest tests/test_phase11_frontend_integration.py` | **5 passed in 5.23s** |
| Phase 13/13.5 Verification | `pytest tests/test_phase13_integration.py tests/test_phase13_5_verification.py` | **12 passed in 12.84s** |
| Phase 17 Audio Enhancement | `pytest tests/test_ai_audio_enhance.py` | **13 passed in 9.75s** |
| Frontend Production Build | `npm run build` | **0 errors, build succeeded** |
| Database Migration State | `alembic current` | **0006_api_keys_and_webhooks (head)** |

---

## 10. Final Acceptance Classification

**PRODUCTION READY**  
**REAL API KEY AUTHENTICATION VALIDATED**  
**REAL WEBHOOK DELIVERY VALIDATED**
