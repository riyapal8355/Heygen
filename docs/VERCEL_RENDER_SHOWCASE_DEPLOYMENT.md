# HeyZen — Vercel + Render Temporary Showcase Deployment Guide

> **NOTICE: TEMPORARY SHOWCASE DEPLOYMENT — NOT PERMANENT PRODUCTION INFRASTRUCTURE**  
> This specification documents how to deploy the current unmodified HeyZen application for public web showcase demonstration using **Vercel** for the Next.js frontend and **Render** for the FastAPI backend and Celery workers, while preserving all existing architectural contracts.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |                 Browser                     |
                                      +----------------------+----------------------+
                                                             |
                                      +----------------------+----------------------+
                                      |       Vercel Next.js Frontend               |
                                      |     (https://<app>.vercel.app)              |
                                      +----------------------+----------------------+
                                                             | HTTPS API & SSE Stream
                                                             | (credentials: include)
                                                             v
                                      +---------------------------------------------+
                                      |         Render FastAPI Web Service          |
                                      |      (https://<service>.onrender.com)       |
                                      +-------+--------------------+----------------+
                                              |                    |
                         +--------------------+                    +-------------------+
                         |                    |                    |                   |
                         v                    v                    v                   v
              +--------------------+ +-----------------+ +-------------------+ +----------------+
              |     PostgreSQL     | |      Redis      | |   MinIO / S3      | |     FFmpeg     |
              | (Managed/External) | | (Queue & Cache) | | (Object Storage)  | | (Media Engine) |
              +--------------------+ +--------+--------+ +-------------------+ +----------------+
                                              |
                                              v
                                     +-----------------+
                                     |  Render Celery  |
                                     | Background      |
                                     | Worker          |
                                     +-----------------+
```

---

## PART A — GitHub

- **Repository**: `https://github.com/riyapal8355/Heygen`
- **Target Branch**: `main`
- **Deployment Monorepo Structure**:
  - Frontend root: `./` (Next.js 16 app in `src/`, `package.json`, `next.config.ts`)
  - Backend root: `backend/` (FastAPI app in `backend/app/`, `requirements.txt`, `alembic.ini`)
  - Shared infrastructure: `infrastructure/` and `render.yaml` at repo root.

---

## PART B — Vercel (Next.js Frontend)

1. **Project Creation**:
   - Log in to [Vercel Dashboard](https://vercel.com).
   - Click **Add New...** → **Project**.
   - Select the GitHub repository: `riyapal8355/Heygen`.
2. **Configuration**:
   - **Framework Preset**: `Next.js` (automatically detected).
   - **Root Directory**: `./` (leave default repository root).
   - **Build Command**: `next build` (or leave default `npm run build`).
   - **Output Directory**: `.next` (automatically managed).
   - **Install Command**: `npm install` (default).
3. **Environment Variables** (Vercel Project Settings → Environment Variables):
   | Variable | Value | Purpose |
   | :--- | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://<your-render-backend>.onrender.com` | Base URL used by browser to query FastAPI backend |
4. **Deploy**:
   - Trigger build. Once deployed, note your assigned Vercel URL (e.g. `https://heyzen.vercel.app`).

---

## PART C — Render (FastAPI Web Service)

Deploy either via **Render Blueprint (`render.yaml`)** or manual Web Service creation:

1. **Service Settings**:
   - **Service Type**: Web Service
   - **Name**: `heyzen-backend`
   - **Runtime**: `Python` (or `Docker` using `infrastructure/docker/Dockerfile.api`)
   - **Root Directory**: `backend`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --proxy-headers --forwarded-allow-ips "*"`
   - **Health Check Path**: `/health`
2. **Environment Variables**:
   | Variable | Example Value | Notes |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.12.8` | Minimum Python 3.12 required |
   | `APP_ENV` | `production` | Enables production security checks |
   | `DEBUG` | `false` | Disables debug stack traces in JSON responses |
   | `DATABASE_URL` | `postgresql+asyncpg://...` | Publicly reachable PostgreSQL URI |
   | `REDIS_URL` | `rediss://...` or `redis://...` | Reachable Redis URI |
   | `MINIO_ENDPOINT` | `https://s3.amazonaws.com` or public MinIO | Storage endpoint |
   | `MINIO_ACCESS_KEY` | `<access-key>` | Storage key |
   | `MINIO_SECRET_KEY` | `<secret-key>` | Storage secret |
   | `MINIO_BUCKET` | `heyzen-assets` | Target S3 bucket |
   | `JWT_SECRET_KEY` | `<32+ char random string>` | Cryptographic token signing key |
   | `FRONTEND_URL` | `https://<your-vercel-domain>.vercel.app` | Vercel production origin for CORS |
   | `COOKIE_SECURE` | `true` | Required for HTTPS cookies |
   | `COOKIE_SAMESITE` | `none` | Required for cross-site Vercel → Render cookies |
   | `AI_PROVIDER_MODE`| `mock` | Fallback mode for CPU showcase |

---

## PART D — Celery (Render Background Worker)

1. **Service Settings**:
   - **Service Type**: Background Worker
   - **Name**: `heyzen-celery-worker`
   - **Runtime**: `Python` (or `Docker` using `infrastructure/docker/Dockerfile.cpu-worker`)
   - **Root Directory**: `backend`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `celery -A app.workers.celery_app.celery_app worker -Q cpu_media,maintenance -c 4 --loglevel=INFO -n cpu_worker@%h`
2. **Environment Variables**:
   - Same `DATABASE_URL`, `REDIS_URL`, `MINIO_*`, and `JWT_SECRET_KEY` as Web Service.

---

## PART E — PostgreSQL Connectivity

- **Requirement**: PostgreSQL requires a publicly reachable / managed production database for the Render deployment (e.g. Render Managed PostgreSQL, Supabase, Neon, or AWS RDS).
- **Driver Specification**: The URI must use the async driver: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`. (If standard `postgresql://` is passed, the backend automatically normalizes it to `postgresql+asyncpg://`).
- **Initial Migration**:
  - Run database migrations from the Render Shell or deployment build step:
    ```bash
    cd backend && alembic upgrade head
    ```
  - The application automatically seeds global canonical presets and roles on startup.

---

## PART F — Redis Connectivity

- **Requirement**: A network-reachable Redis instance is required for Celery broker, Celery backend, rate limiting, and real-time SSE job event pub/sub.
- **Provider Options**: Render Redis, Upstash, or cloud Redis.
- **TLS Note**: For SSL-enabled cloud Redis endpoints, specify `rediss://...`.

---

## PART G — MinIO / Object Storage Connectivity

- **Requirement**: The Render backend generates pre-signed PUT upload intents and pre-signed GET download URLs. The storage endpoint must be reachable both by the backend and by the end user's browser.
- If using AWS S3, Cloudflare R2, or Wasabi:
  - Set `MINIO_ENDPOINT=https://s3.<region>.amazonaws.com` (or R2 endpoint).
  - Pre-signed URLs will direct the browser straight to object storage.
- If using self-hosted MinIO: ensure the endpoint has a valid HTTPS certificate and is accessible on public internet.

---

## PART H — CORS (Cross-Origin Resource Sharing)

- The FastAPI backend includes `CORSMiddleware` configured with:
  - `allow_credentials=True`
  - `allow_methods=["*"]`
  - `allow_headers=["*"]`
  - `expose_headers=["X-Request-ID", "X-Process-Time-Ms"]`
- Configured via `FRONTEND_URL` environment variable:
  ```env
  FRONTEND_URL=https://your-vercel-domain.vercel.app
  ```
- Local origins (`http://localhost:3000`, `http://127.0.0.1:3000`) are always preserved.

---

## PART I — Authentication & Cross-Origin Cookies

- **Session Security**:
  - Access token: transmitted in JSON and stored in memory/localStorage by frontend client, passed in `Authorization: Bearer <token>`.
  - Refresh token: transmitted in HttpOnly cookie (`heyzen_refresh_token`).
- **Cross-Site Cookie Contract**:
  - Vercel (`*.vercel.app`) and Render (`*.onrender.com`) are cross-site third-party origins.
  - Modern browsers require:
    - `SameSite=None`
    - `Secure=True`
  - Set in Render Web Service environment variables:
    ```env
    COOKIE_SECURE=true
    COOKIE_SAMESITE=none
    ```
- **Fallback**: The backend `/api/v1/auth/refresh` endpoint also supports reading the token candidate directly from the request JSON body for clients with strict third-party cookie blocking.

---

## PART J — Media & FFmpeg Execution

- The backend invokes `ffmpeg` and `ffprobe` for media probing, audio normalization, clip trimming, and video composition.
- **Render Native Python**: Standard Render Python runtime does not include system `ffmpeg`. If deployed as a native Python service without FFmpeg installed, media operations will fall back to mock probing or fail.
- **Recommended for Full Media Processing**: Deploy the Render Web Service and Worker using the existing Dockerfiles:
  - Web Service: `infrastructure/docker/Dockerfile.api`
  - Celery Worker: `infrastructure/docker/Dockerfile.cpu-worker`
  Both Dockerfiles install `ffmpeg`, `libsm6`, `libxext6`, `libgl1`, and all required media libraries.

---

## PART K — AI & GPU Limitation

- **Crucial Limitation**: Avatar generation requires the existing GPU-capable infrastructure.
- In a CPU-only Render showcase environment, the backend will truthfully report `GPU_REQUIRED` and fail truthfully rather than generating fake video or synthetic output.
- **Policy**:
  - Legacy Wav2Lip/Delaunay generation remains permanently blocked in production.
  - Video Agent workspace accurately surfaces GPU requirements to users.

---

## PART L — Verification Checklist

Before opening the showcase to the public, verify the live deployment:

1. **Backend Liveness**:
   ```bash
   curl -I https://<render-service>.onrender.com/health
   # Expected: HTTP 200 OK {"status":"ok","app":"HeyZen Backend",...}
   ```
2. **Backend Readiness**:
   ```bash
   curl https://<render-service>.onrender.com/ready
   # Expected: {"status":"ready","checks":{"database":"ok","redis":"ok","storage":"ok"}}
   ```
3. **Frontend Load**:
   - Open `https://<vercel-domain>.vercel.app` in browser.
   - Verify landing page loads, login modal appears, and theme toggle works.
4. **Authentication Flow**:
   - Register or log in with test credentials.
   - Refresh page; verify session persists without redirecting to login.
5. **Brand Systems & Projects**:
   - Open Brand Systems; verify default presets render.
   - Create a test project; verify OCC version snapshot saves successfully.
