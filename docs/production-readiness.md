# HeyZen Autonomous AI Video Studio — Production Readiness & Deployment Guide

> **Document Status**: Complete & Authoritative  
> **Backend Architecture**: Production-Hardened & Containerized  
> **Development Host**: AMD Ryzen 5 5500U (12 Cores, 16 GB RAM, CPU-only)  
> **Overall Production State**: `PRODUCTION HARDENING COMPLETE — GPU VALIDATION PENDING`

---

## 1. Executive Summary & System Classification

HeyZen is a multi-tenant autonomous AI video generation platform and studio backend. This document specifies the comprehensive production architecture, deployment topology, security policies, backup/restore runbooks, and validation checklists.

### Component Readiness Matrix

| Component | Architecture State | Local CPU Validation | Production Target Status |
| :--- | :--- | :--- | :--- |
| **FastAPI REST & SSE API** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Multi-Tenancy Isolation** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Authentication & Sessions** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Asset Storage & Upload Security** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **PostgreSQL 16 & Connection Pool** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Redis 7 Broker, Cache & Limiter** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Celery CPU Worker (`cpu_media`)** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Celery Maintenance Worker** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **CPU AI Capabilities (TTS, ASR, VAD, etc.)** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Nginx Reverse Proxy & SSL/SSE** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **PostgreSQL Backup & Restore** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **CI/CD Invariant Gates** | IMPLEMENTED | TESTED | **DEPLOYMENT READY** |
| **Celery GPU Worker (`gpu_ai`)** | IMPLEMENTED | STRUCTURALLY TESTED | **CUDA VALIDATION PENDING** |
| **MuseTalk Lip-Sync Inference** | IMPLEMENTED | STRUCTURALLY TESTED | **CUDA VALIDATION PENDING** |
| **Stable Diffusion v1.5 Inference** | IMPLEMENTED | STRUCTURALLY TESTED | **CUDA VALIDATION PENDING** |

---

## 2. Deployment Topology & Multi-Container Architecture

Production deployment runs via container orchestration (Docker Compose / Kubernetes) with strict boundary isolation between stateless services, storage, and worker queues:

```
                      Internet / Client Browsers
                                  │
                                  ▼ (Port 80 -> 301 HTTPS / Port 443 TLS)
                      ┌──────────────────────┐
                      │     Nginx Proxy      │
                      │ (SSL, SSE, Rate Lim) │
                      └──────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼ (/api/*, /health, /metrics)    ▼ (/*)
       ┌──────────────────┐             ┌─────────────────────┐
       │   FastAPI API    │             │   Next.js Frontend  │
       │ (4 Uvicorn Wkrs) │             │ (Frozen Standalone) │
       └─────────┬────────┘             └─────────────────────┘
                 │
  ┌──────────────┼───────────────────────────┐
  │              │                           │
  ▼              ▼                           ▼
┌──────────────┐ ┌──────────────────────┐   ┌────────────────────────┐
│  PostgreSQL  │ │        Redis 7       │   │   MinIO / AWS S3       │
│  (Port 5432) │ │ (Broker, Cache, Lim) │   │ (Assets & Media Store) │
└──────────────┘ └──────────┬───────────┘   └──────────┬─────────────┘
                            │                          │
                 ┌──────────┴───────────────┐          │
                 │                          │          │
                 ▼                          ▼          ▼
       ┌──────────────────┐       ┌───────────────────────────┐
       │ Celery CPU Worker│       │  Celery GPU Worker        │
       │  (`cpu_media`,   │       │  (`gpu_ai`, Concurrency=1,│
       │   `maintenance`) │       │   NVIDIA CUDA 12.4 Device)│
       └──────────────────┘       └───────────────────────────┘
```

---

## 3. Environment Variables & Production Secrets

Production enforces **fail-closed startup validation**: if `APP_ENV=production`, the application crashes on boot if any secret is default, insecure, or truncated.

| Variable | Description | Security Requirement / Format | Production Example |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | Environment identifier | Must be `production` | `production` |
| `DEBUG` | Debug flag | **MUST be `false`** | `false` |
| `DATABASE_URL` | Asyncpg connection URI | Strong credentials; no `heyzen_dev_password` | `postgresql+asyncpg://usr:str0ngPass!@db.internal:5432/heyzen` |
| `REDIS_URL` | Redis URI | Secure password-protected instance | `redis://:str0ngRedisPass!@redis.internal:6379/0` |
| `JWT_SECRET_KEY` | JWT HS256 signing secret | $\ge 32$ cryptographic random characters | `c9f0a82b3d7e4125892c9431e7b8a531649204...` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | Default 15 minutes | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan | Default 7 days | `7` |
| `MINIO_ENDPOINT` / `S3_ENDPOINT` | Storage endpoint | HTTPS / internal domain | `https://s3.us-east-1.amazonaws.com` |
| `MINIO_ACCESS_KEY` / `S3_ACCESS_KEY` | Storage Access Key | IAM access key | `AKIAIOSFODNN7EXAMPLE` |
| `MINIO_SECRET_KEY` / `S3_SECRET_KEY` | Storage Secret Key | Strong secret; no `heyzen_dev_password123` | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `MINIO_BUCKET` / `S3_BUCKET` | Dedicated assets bucket | Bucket name | `heyzen-prod-assets` |
| `CORS_ORIGINS` | Permitted origins | Comma-separated; **NO `*` with credentials** | `https://app.heyzen.ai,https://studio.heyzen.ai` |
| `COOKIE_SECURE` | HTTPS-only cookies | Must be `true` | `true` |
| `COOKIE_SAMESITE` | Cookie CSRF policy | `lax` or `strict` | `lax` |
| `DB_POOL_SIZE` | SQLAlchemy pool size | 5 to 50 | `20` |
| `DB_MAX_OVERFLOW` | SQLAlchemy overflow | 10 to 50 | `30` |
| `DB_POOL_TIMEOUT` | Pool wait timeout | Seconds | `30` |
| `DB_POOL_RECYCLE` | Connection recycle | Seconds (default 1800) | `1800` |
| `RATE_LIMIT_AUTH_PER_MINUTE` | Auth attempt rate limit | Per IP per minute | `10` |
| `RATE_LIMIT_UPLOAD_PER_MINUTE`| Upload intent rate limit | Per user per minute | `30` |
| `AI_RUNTIME_MODE` | AI execution runtime | `real` in production | `real` |
| `AI_ALLOW_AUTO_DOWNLOAD` | Strict weight guard | **MUST be `false`** | `false` |
| `AI_VERIFY_CHECKSUMS` | Model integrity guard | **MUST be `true`** | `true` |

---

## 4. Multi-Tenancy & Workspace Isolation

HeyZen enforces strict tenant isolation at the data layer:
1. Every workspace-scoped entity (`Project`, `Folder`, `Asset`, `Job`, `ProjectVersion`, `Scene`) has a mandatory `workspace_id` foreign key.
2. In `app/api/deps.py`, the `require_permission(perm)` dependency verifies that the authenticated `current_user` has an active `WorkspaceMember` association with the targeted `workspace_id`.
3. Database queries filter by `(workspace_id, id)` composite predicates. Cross-tenant reads or writes return `HTTP 403 Forbidden` or `HTTP 404 Not Found`.
4. Storage keys are generated strictly server-side: `workspaces/{workspace_id}/assets/{asset_id}/{filename}`. Tenants cannot guess or access S3 keys outside their workspace.

---

## 5. Security & Attack Surface Hardening

### Authentication & Sessions
- **Password Hashing**: Argon2id with salt generation via Passlib.
- **Access Tokens**: Short-lived JWTs (15 minutes), signed with HMAC-SHA256 using production keys $\ge 32$ chars.
- **Refresh Tokens**: Cryptographically random 64-byte tokens stored in `user_sessions` as SHA-256 hashes. Stored on clients exclusively as `HttpOnly`, `Secure`, `SameSite=Lax` cookies. Revoked immediately upon logout or password change.
- **Session Rotation**: On refresh, the previous refresh token is deleted and replaced with a newly generated session.

### Upload Security
- **Path Traversal Protection**: User-supplied filenames are sanitized with `os.path.basename` and stripped of `/`, `\\`, and `..` components.
- **Executable Blocking**: Prohibits upload intents for `.exe`, `.bat`, `.cmd`, `.sh`, `.bash`, `.php`, `.py`, `.js`, `.ps1`, `.msi`, `.dll`, `.so`, `.dylib`, `.vbs`, etc.
- **Size Bounds Enforcement**: Max upload size capped at `MAX_MEDIA_INPUT_SIZE_BYTES` (500 MB). Negative sizes or sizes $> 500$ MB are rejected with `HTTP 409 Conflict`.
- **Pre-signed Direct Upload**: Uploads bypass application web servers and stream directly to MinIO/S3 via pre-signed PUT URLs with 15-minute expiration.

### Rate Limiting
- Redis-backed atomic sliding-window rate limiters protect sensitive endpoints:
  - `/api/v1/auth/signup` and `/api/v1/auth/login`: 10 requests / minute / IP
  - `/api/v1/workspaces/{id}/assets/upload-intents`: 30 requests / minute / user
  - AI Orchestration & Rendering: 20 requests / minute / user
- Exceeded thresholds return `HTTP 429 Too Many Requests` with standard `Retry-After` headers.

---

## 6. Database Production Architecture & Maintenance

### SQLAlchemy Connection Pool
- Engine initialized with `create_async_engine(settings.DATABASE_URL)`.
- Features `pool_pre_ping=True` to detect and transparently reconnect dropped PostgreSQL connections.
- Configurable pool sizing: `pool_size=settings.DB_POOL_SIZE`, `max_overflow=settings.DB_MAX_OVERFLOW`, `pool_recycle=1800` (recycles connections every 30 minutes to prevent resource creep).

### Automated Backup Procedure
Script: `backend/scripts/backup_db.py`
- Operates either via Docker (`docker exec heyzen-postgres pg_dump`) or native `pg_dump`.
- Streams compressed SQL archives into `backend/backups/heyzen_backup_YYYYMMDD_HHMMSS.sql.gz`.
- Computes and logs SHA-256 checksum and uncompressed/compressed byte sizes.
- Automated retention: prunes archives older than `--retention-days` (default 7 days).
- **Execution**:
  ```bash
  python backend/scripts/backup_db.py --retention-days 14
  ```

### Automated Restore Procedure
Script: `backend/scripts/restore_db.py`
- Decompresses `.sql.gz` and pipes to `psql` in a transaction.
- Requires explicit confirmation flag (`--confirm`) or typing `RESTORE` to prevent accidental overwrites.
- Performs post-restore sanity check: validates workspace count.
- **Execution**:
  ```bash
  python backend/scripts/restore_db.py --latest --confirm
  ```

---

## 7. Storage (MinIO & AWS S3)

The application uses an abstract `StorageProvider` interface (`app.storage.base.StorageProvider`) with concrete S3/MinIO implementation (`app.storage.s3.S3StorageProvider`).

### Production S3 Migration
To switch from local MinIO to AWS S3:
1. Set `S3_ENDPOINT=https://s3.<region>.amazonaws.com`.
2. Set `S3_ACCESS_KEY` and `S3_SECRET_KEY` with appropriate IAM role permissions (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:HeadObject`).
3. Set `S3_BUCKET` to your dedicated bucket name.
4. The application seamlessly routes all pre-signed URLs and object operations without any code changes.

---

## 8. Asynchronous Processing & Celery Queue Topology

### Queues
1. `cpu_media`: Multi-threaded CPU worker (`-c 4`). Processes FFmpeg concatenation, audio mixing, Piper TTS, Silero VAD, MediaPipe matting.
2. `gpu_ai`: Single-task dedicated GPU worker (`-c 1`, `--max-tasks-per-child=50`). Consumes MuseTalk lip-sync and Stable Diffusion image generation. Strictly fails closed if no CUDA GPU is detected.
3. `maintenance`: Scheduled housekeeping tasks, including stale job reaping and orphan asset purging.

### Celery Reliability Invariants
- `task_acks_late=True`: Tasks are acknowledged only after successful completion, ensuring worker crashes return jobs to the queue.
- `worker_prefetch_multiplier=1`: Prevents workers from hoarding tasks they cannot immediately process.
- `reap_stale_jobs`: Periodic task marks jobs stuck in `running` status longer than timeout as `failed` with diagnostic error codes.

---

## 9. Telemetry, Health & Monitoring

Endpoints exposed for infrastructure monitoring:
1. `GET /health`: Liveness probe. Returns `HTTP 200 OK` if the FastAPI process is responsive.
2. `GET /ready`: Readiness probe. Pings PostgreSQL, Redis, and MinIO/S3. Returns `HTTP 200` if all 3 are healthy, or `HTTP 503` if any service is down.
3. `GET /health/ai`: AI capability and hardware probe. Reports CPU model, RAM, and GPU status (`CUDA unavailable` or GPU model/VRAM).
4. `GET /metrics`: Telemetry snapshot including API request counts, latency averages/percentiles, error rates, job state transitions, and subsystem errors.

---

## 10. Reverse Proxy & HTTPS (Nginx)

Configuration: `infrastructure/nginx/nginx.conf` and `infrastructure/nginx/conf.d/heyzen.conf`
- **TLS Termination**: Enforces TLS 1.2 and TLS 1.3 with modern secure ciphers.
- **Server-Sent Events (SSE)**: `proxy_buffering off;` and `proxy_cache off;` on `/api/v1/jobs/*/events` ensures real-time client job updates without buffering delay.
- **High-Capacity Media**: `client_max_body_size 500M;` and `client_body_timeout 300s;` accommodate 4K video uploads.

---

## 11. CI/CD Pipeline & Invariant Enforcement

GitHub Actions: `.github/workflows/ci.yml`
Enforces 5 mandatory gates:
1. **Frontend Frozen Verification**: Fails immediately if any file in `src/**`, `public/**`, `package.json`, or `package-lock.json` is modified.
2. **Alembic Head Verification**: Fails if new migrations are added or the head deviates from `0005_jobs_task_pipeline`.
3. **Docker Config Validation**: Validates syntax of `docker-compose.yml`, `docker-compose.prod.yml`, and `docker-compose.gpu.yml`.
4. **Code Quality & Syntax**: Python bytecode compilation check (`python -m compileall`).
5. **Full Regression Test Matrix**: Runs full pytest test suite against containerized PostgreSQL, Redis, and MinIO services.

---

## 12. GPU Validation Procedure (When NVIDIA Hardware Arrives)

When deploying to a host with an NVIDIA GPU (e.g., RTX 3080/4090, A10G, T4, L4):

1. **Hardware Verification**:
   ```bash
   nvidia-smi
   ```
   Ensure NVIDIA driver $\ge 535$ and CUDA runtime 12.4 are accessible.

2. **Model Provisioning**:
   ```bash
   python backend/scripts/provision_gpu_models.py --verify-only
   ```
   Ensures MuseTalk and Stable Diffusion weights exist in `models_cache` with matching SHA-256 hashes.

3. **Start GPU Worker**:
   ```bash
   docker compose -f infrastructure/docker/docker-compose.gpu.yml up -d
   ```

4. **Execute GPU Acceptance Suite**:
   ```bash
   pytest backend/tests/test_gpu_worker_routing.py -v
   pytest backend/tests/test_ai_avatar.py -v
   pytest backend/tests/test_ai_image_gen.py -v
   ```

5. **Verify AI Health**:
   ```bash
   curl -s http://localhost:8000/health/ai | jq .gpu_worker
   ```
   Verify `"cuda_available": true`, `"ready": true`, and VRAM reported.
