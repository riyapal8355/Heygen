# HeyZen Developer Setup & Operations Guide

This guide provides complete, step-by-step instructions for provisioning, running, configuring, and verifying the HeyZen autonomous AI video platform on Windows, macOS, and Linux.

---

## 1. System Prerequisites

The following software binaries and runtimes must be installed on your workstation:

| Component | Verified Version | Purpose | Download / Command |
|---|---|---|---|
| **Node.js** | `v24.13.1` (or >= 20.x) | Next.js frontend runtime | [nodejs.org](https://nodejs.org/) (`node -v`) |
| **npm** | `11.11.1` (or >= 10.x) | Frontend package manager | Bundled with Node (`npm -v`) |
| **Python** | `3.13.7` (or >= 3.11.x) | Backend API & Celery worker runtime | [python.org](https://python.org/) (`python -V`) |
| **Docker Desktop** | `29.7.2` (or >= 24.x) | Container runtime for Postgres, Redis, MinIO | [docker.com](https://www.docker.com/) (`docker --version`) |
| **FFmpeg** | `9.0.1-essentials` | Media decoding, scaling, filtergraphs & MP4 assembly | [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (`ffmpeg -version`) |
| **FFprobe** | `9.0.1-essentials` | Audio/video metadata extraction & validation | Bundled with FFmpeg (`ffprobe -version`) |
| **Google Chrome** | Latest Stable | Used as the browser channel for Playwright E2E tests | [google.com/chrome](https://www.google.com/chrome/) |
| **NVIDIA CUDA** *(Optional)* | CUDA `12.4.1` + Driver >= 550 | GPU-accelerated diffusion & neural avatar generation | Optional; CPU mode fully supported |

> [!NOTE]
> If a dedicated NVIDIA GPU is not detected or CUDA packages are omitted, HeyZen operates deterministically in **CPU Mode** using faster-whisper, Piper TTS, Kokoro ONNX, CTranslate2, and CPU Wav2Lip fallback.

---

## 2. Windows Quick-Start Setup

Execute the following commands in PowerShell from the repository root (`D:\HeyGen\video-ai-tools`):

### Step 1: Frontend Dependency Installation
```powershell
# Install Node dependencies
npm install
```

### Step 2: Python Virtual Environment & Backend Dependencies
```powershell
# Navigate into backend
cd backend

# Create dedicated virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install CPU / core dependencies
pip install -r requirements.txt

# (Optional) If NVIDIA CUDA 12.4 is available and GPU workloads are required:
# pip install -r requirements-gpu.txt

cd ..
```

### Step 3: Infrastructure Services (PostgreSQL, Redis, MinIO)
Using Docker Compose:
```powershell
# Start PostgreSQL (5432), Redis (6379), and MinIO S3 (9000/9001)
docker compose up -d postgres redis minio
```

Verify that all three services report healthy:
```powershell
docker compose ps
```

*Port Mapping Table:*
- PostgreSQL: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- MinIO S3 API: `127.0.0.1:9000`
- MinIO Web Console: `127.0.0.1:9001` (User: `heyzen_admin`, Pass: `heyzen_dev_password123`)

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` in the repository root:
```powershell
Copy-Item .env.example .env
```

### Environment Variables Inventory

| Variable | Purpose | Required | Default / Example | Format / Notes |
|---|---|---|---|---|
| `APP_ENV` | Environment classification | Yes | `development` | `development`, `test`, `production` |
| `APP_NAME` | Human-readable app name | No | `HeyZen Backend` | String |
| `APP_VERSION` | Application semantic version | No | `0.1.0` | SemVer string |
| `DEBUG` | Enable verbose logging & OpenAPI docs | No | `true` | Boolean (`true`/`false`) |
| `DATABASE_URL` | Async SQLAlchemy database URI | Yes | `postgresql+asyncpg://heyzen:heyzen_dev_password@127.0.0.1:5432/heyzen` | Must use `postgresql+asyncpg://` |
| `POSTGRES_DB` | PostgreSQL database name | No | `heyzen` | String |
| `POSTGRES_USER` | PostgreSQL user | No | `heyzen` | String |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes | `heyzen_dev_password` | Alphanumeric string |
| `REDIS_URL` | Redis URI for Celery broker & Pub/Sub | Yes | `redis://127.0.0.1:6379/0` | URI string |
| `MINIO_ENDPOINT` | MinIO / S3 object storage endpoint | Yes | `http://127.0.0.1:9000` | HTTP URL |
| `MINIO_ROOT_USER` | MinIO admin user | Yes | `heyzen_admin` | String |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | Yes | `heyzen_dev_password123` | Alphanumeric string |
| `MINIO_ACCESS_KEY` | MinIO access key identifier | Yes | `heyzen_admin` | String |
| `MINIO_SECRET_KEY` | MinIO secret access key | Yes | `heyzen_dev_password123` | Alphanumeric string |
| `MINIO_BUCKET` | Default media bucket name | No | `heyzen-assets` | Lowercase bucket identifier |
| `MINIO_REGION` | S3 region identifier | No | `us-east-1` | S3 region string |
| `JWT_SECRET_KEY` | Secret key for JWT HS256 signing | Yes | *(Dev placeholder in .env.example)* | >= 32 characters in production |
| `JWT_ALGORITHM` | JWT signing algorithm | No | `HS256` | Must be `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | No | `15` | Integer minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan | No | `7` | Integer days |
| `CORS_ORIGINS` | Comma-separated allowed web origins | Yes | `http://localhost:3000,http://127.0.0.1:3000` | URLs without wildcards |
| `COOKIE_SECURE` | HTTPS flag for refresh cookie | No | `false` (True in prod) | Boolean |
| `COOKIE_SAMESITE` | SameSite cookie policy | No | `lax` | `lax`, `strict`, `none` |
| `AI_PROVIDER_MODE` | AI Provider adapter mode | No | `mock` (`real` for production) | `mock` or `real` |
| `AI_RUNTIME_MODE` | AI hardware execution mode | No | `mock` (`real` for production) | `mock` or `real` |
| `AI_PREFERRED_DEVICE` | Compute device selection | No | `auto` | `auto`, `cpu`, `cuda` |
| `AI_MODEL_CACHE_DIR` | Local disk cache for models | No | `models_cache` | Path relative or absolute |
| `AI_MAX_CPU_MEMORY_MB` | Maximum CPU RAM for AI models | No | `4096` | Integer megabytes |
| `AI_MAX_GPU_MEMORY_MB` | Maximum GPU VRAM for models | No | `0` (or VRAM in MB) | Integer megabytes |
| `AI_ALLOW_AUTO_DOWNLOAD` | Permit automatic weights download | No | `false` | Boolean |
| `AI_VERIFY_CHECKSUMS` | Strict SHA-256 model verification | No | `true` | Boolean |
| `FFMPEG_PATH` | Path to FFmpeg binary | No | `ffmpeg` | Binary name or absolute path |
| `FFPROBE_PATH` | Path to FFprobe binary | No | `ffprobe` | Binary name or absolute path |
| `MEDIA_TIMEOUT_SECONDS` | Max duration per media subprocess | No | `300` | Integer seconds |
| `MAX_VIDEO_DURATION_SECONDS` | Max video duration ceiling | No | `3600.0` (1 hour) | Float seconds |
| `MIN_VIDEO_DURATION_SECONDS` | Minimum video duration floor | No | `5.0` | Float seconds |
| `NEXT_PUBLIC_API_URL` | Frontend API backend origin | Yes | `http://127.0.0.1:8000` | HTTP URL |

---

## 4. Database Migrations & Seeds

With PostgreSQL running, execute Alembic migrations to construct the database schema:

```powershell
cd backend
.\.venv\Scripts\alembic.exe upgrade head
cd ..
```

*Expected Output:*
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_user_schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_user_schema -> 0002_workspaces_and_auth
INFO  [alembic.runtime.migration] Running upgrade 0002_workspaces_and_auth -> 0003_projects_folders_assets
INFO  [alembic.runtime.migration] Running upgrade 0003_projects_folders_assets -> 0004_creative_library
INFO  [alembic.runtime.migration] Running upgrade 0004_creative_library -> 0005_jobs_and_task_pipeline
INFO  [alembic.runtime.migration] Running upgrade 0005_jobs_and_task_pipeline -> 0006_api_keys_and_webhooks
```

### Seeding Presets & Development Fixtures
When the FastAPI backend starts up in `development` mode, it automatically executes:
1. `seed_canonical_presets()`: Seeds 6 canonical avatars (Annie, Marcus, Serena, Alex, Elena, David) and 6 Piper TTS voices.
2. `seed_development_fixtures()`: Creates standard development user `dev@heyzen.ai` (`DevPassword123!`) and default workspace `Default Workspace`.

---

## 5. Starting the Development Stack

To run the complete interactive platform, launch three terminal windows:

### Terminal 1: FastAPI API Gateway
```powershell
cd D:\HeyGen\video-ai-tools\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Swagger UI Documentation: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`
- Health Probe: `http://127.0.0.1:8000/health`

### Terminal 2: Celery Asynchronous Media & AI Worker
> [!IMPORTANT]
> On Windows, Celery's default `prefork` execution pool causes `ValueError` or silent crashes. Always specify `-P solo` or `--pool=threads` when running on Windows!

```powershell
cd D:\HeyGen\video-ai-tools\backend
.\.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker -Q cpu_media,maintenance --loglevel=info -P solo
```

### Terminal 3: Next.js Frontend Application
```powershell
cd D:\HeyGen\video-ai-tools
npm run dev
```
- Application Web Interface: `http://127.0.0.1:3000` (or `http://localhost:3000`)

---

## 6. Running Test Suites

### 1. Frontend Unit Tests (Fast & Deterministic)
Executes native Node test runner on all 89 test suites in `src/lib/*.test.ts`:
```powershell
npm test
```
*Current Verification*: **353 tests passing** (0 failures, duration ~2.1s).

### 2. Backend Unit & Contract Tests
Executes Pytest in the Python virtual environment:
```powershell
cd backend
.\.venv\Scripts\pytest.exe tests/test_config.py tests/test_ai_contracts.py tests/test_flexible_video_durations.py
cd ..
```
*Current Verification*: Config, Pydantic schemas, and flexible video durations pass synchronously.

### 3. Playwright End-to-End Smoke Tests
HeyZen utilizes Playwright configured with the system Google Chrome binary to eliminate flaky multi-hundred-megabyte browser binary downloads.

**Playwright Chrome Channel Configuration** (`playwright.config.ts`):
```typescript
use: {
  baseURL: "http://localhost:3000",
  channel: "chrome",
  headless: true,
}
```

**Running E2E Smoke Tests**:
```powershell
# Ensure Terminal 1 (FastAPI) and Terminal 3 (Next.js) are running, then:
npx playwright test tests/e2e/smoke.spec.ts
```

**Running Auth Persistence Tests**:
```powershell
npx playwright test tests/e2e/auth-persistence.spec.ts
```

---

## 7. Troubleshooting Guide

| Symptom / Error | Root Cause | Verification Check | Recommended Fix |
|---|---|---|---|
| `botocore.exceptions.EndpointConnectionError: Could not connect to http://127.0.0.1:9000` | MinIO object storage container is stopped | Run `docker compose ps` | Start MinIO with `docker compose up -d minio` |
| `ValueError: Unsupported schema_version: X. Expected 1.` | Project JSON document version mismatch | Check `document["schema_version"]` | Must always be integer `1` |
| `Revision conflict: current revision is X, but requested Y` | Optimistic Concurrency Control (OCC) collision | Inspect `project.revision` vs `expected_revision` | Re-fetch the latest `current_version_id` and document before submitting modifications |
| `Celery: PermissionError / ValueError on Windows` | Celery prefork pool incompatible with Windows OS | Review Celery startup command | Append `-P solo` to the Celery command: `celery -A app.workers.celery_app worker -P solo` |
| `CORS Error: Response to preflight request doesn't pass access control check` | Client origin not included in `CORS_ORIGINS` | Check `CORS_ORIGINS` in `.env` | Add `http://localhost:3000,http://127.0.0.1:3000` without trailing slashes |
| `JWT_SECRET_KEY must be a cryptographically strong secret in production` | Production fail-closed check caught insecure secret | Inspect `APP_ENV` and `JWT_SECRET_KEY` | Set a unique random secret of >= 32 characters in production |
| `Playwright: Executable doesn't exist at C:\Users\...\AppData\Local\ms-playwright\chromium` | Playwright browser download skipped or blocked | Check `playwright.config.ts` | Verify `channel: "chrome"` is active in `playwright.config.ts` so system Chrome is utilized |
| `Theme flicker / Flash of dark theme before light applies` | Theme script ran after hydration | Inspect `<head>` in `src/app/layout.tsx` | Ensure the inline `<script>` in `<head>` reads `localStorage.getItem('vidoai_theme')` and sets `classList.add('light')` |
| `FFmpeg: filter 'xfade' not found or unknown option` | Outdated FFmpeg binary (< version 4.3) | Run `ffmpeg -version` | Install FFmpeg version 6.x, 7.x, 8.x, or 9.x |

---

## 8. Production Multi-Container Deployment

In production environments, HeyZen deploys via `docker-compose.prod.yml` with strict resource limits and automated health checks:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

### Production Topology Architecture:
1. **`postgres`** (PostgreSQL 16-alpine): 2 CPUs, 4GB RAM ceiling, persistent volume `heyzen_postgres_data`.
2. **`redis`** (Redis 7-alpine): 1 CPU, 1.5GB RAM ceiling, append-only persistence `heyzen_redis_data`.
3. **`minio`** (MinIO S3): 1.5 CPUs, 2GB RAM ceiling, persistent bucket storage `heyzen_minio_data`.
4. **`api`** (FastAPI Gateway): 4 CPUs, 4GB RAM ceiling, Uvicorn production server.
5. **`cpu-worker`** (Celery CPU media compositor & local AI): 4 CPUs, 6GB RAM ceiling, mounted `heyzen_models_cache`.
6. **`nginx`** (Reverse Proxy & SSL Termination): 1 CPU, 512MB RAM ceiling, HTTP/2 + SSE unbuffered streaming.
