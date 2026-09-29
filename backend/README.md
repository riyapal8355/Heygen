# HeyZen Backend Foundation

Asynchronous FastAPI backend foundation for HeyZen AI Video Studio.

## Architecture

* **Framework:** FastAPI with Python 3.12+ / 3.13
* **Database:** PostgreSQL 16 via SQLAlchemy 2.x (asyncpg)
* **Migrations:** Alembic (async runner)
* **Broker & Cache:** Redis 7
* **Job Engine:** Celery 5.x
* **Object Storage:** MinIO / AWS S3 via boto3
* **Authentication Security:** Argon2id password hashing + PyJWT tokens

## Directory Structure

```text
backend/
├── app/
│   ├── main.py                  # FastAPI application entrypoint & middleware
│   ├── api/                     # Routing, middleware, v1 endpoints
│   ├── core/                    # Config, logging, security, Redis pool
│   ├── db/                      # SQLAlchemy session, engine, base models
│   ├── models/                  # Domain models (User, UserCredential)
│   ├── schemas/                 # Pydantic v2 schemas
│   ├── repositories/            # Data access layer
│   ├── services/                # Business logic services
│   ├── storage/                 # StorageProvider abstraction (S3/MinIO)
│   ├── workers/                 # Celery app and background tasks
│   └── ai/                      # Vendor-independent AI interfaces
├── alembic/                     # Database migrations
├── tests/                       # Pytest test suite
├── pyproject.toml               # Dependencies and build configuration
└── alembic.ini                  # Alembic configuration
```

## Running Locally

### 1. Activate Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run Database Migrations
```powershell
alembic upgrade head
```

### 3. Run Automated Tests
```powershell
pytest
```

### 4. Run Development Server
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
