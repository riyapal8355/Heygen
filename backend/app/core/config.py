"""Application configuration using Pydantic Settings v2.

Reads from environment variables and root / local .env files.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Information
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    APP_NAME: str = Field(default="HeyZen Backend", description="Human-readable application name")
    APP_VERSION: str = Field(default="0.1.0", description="SemVer application version")
    DEBUG: bool = Field(default=True, description="Debug mode flag")

    # Database (PostgreSQL)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://heyzen:heyzen_dev_password@127.0.0.1:5432/heyzen",
        description="Async SQLAlchemy database connection URI",
    )

    # Redis (Broker, Cache, Pub/Sub)
    REDIS_URL: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Redis connection URI",
    )

    # MinIO / S3 Object Storage
    MINIO_ENDPOINT: str = Field(default="http://127.0.0.1:9000", description="MinIO/S3 endpoint URL")
    MINIO_ACCESS_KEY: str = Field(default="heyzen_admin", description="S3 Access Key")
    MINIO_SECRET_KEY: str = Field(default="heyzen_dev_password123", description="S3 Secret Key")
    MINIO_BUCKET: str = Field(default="heyzen-assets", description="S3 default bucket name")
    MINIO_REGION: str = Field(default="us-east-1", description="S3 region name")

    # Backwards-compatible aliases if S3_* are provided in environment
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET: str | None = None

    # JWT & Authentication
    JWT_SECRET_KEY: str = Field(
        default="dev_insecure_jwt_secret_key_for_local_testing_only_replace_in_prod",
        description="Cryptographic secret key for JWT signing",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, description="Access token expiration in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration in days")

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Allowed CORS origins as comma-separated string or list",
    )
    FRONTEND_URL: Optional[str] = Field(
        default=None,
        description="Optional production frontend origin URL (e.g. Vercel deployment URL)",
    )

    # AI Provider & Runtime Foundation Defaults
    AI_PROVIDER_MODE: str = Field(default="mock", description="AI Provider execution mode: mock or real")
    AI_RUNTIME_MODE: str = Field(default="mock", description="AI Runtime execution mode: mock or real")
    AI_PREFERRED_DEVICE: str = Field(default="auto", description="Preferred compute device: auto, cpu, or cuda")
    AI_MODEL_CACHE_DIR: str = Field(default="models_cache", description="Directory path for cached AI models")
    AI_MAX_CPU_MEMORY_MB: int = Field(default=4096, description="Max CPU memory limit in MB for local AI models")
    AI_MAX_GPU_MEMORY_MB: int = Field(default=0, description="Max GPU VRAM limit in MB (0 if no GPU detected/configured)")
    AI_ALLOW_AUTO_DOWNLOAD: bool = Field(default=False, description="Strict policy: prevent multi-GB auto downloads during API requests")
    AI_VERIFY_CHECKSUMS: bool = Field(default=True, description="Strict policy: verify SHA-256 model checksums before loading")
    AI_INFERENCE_TIMEOUT_SECONDS: int = Field(default=120, ge=5, le=3600, description="Max execution duration for local AI inference")
    DEFAULT_LLM_PROVIDER: str = Field(default="mock", description="Default active LLM provider")
    DEFAULT_TTS_PROVIDER: str = Field(default="mock", description="Default active TTS provider")
    DEFAULT_ASR_PROVIDER: str = Field(default="mock", description="Default active ASR provider")
    DEFAULT_TRANSLATION_PROVIDER: str = Field(default="mock", description="Default active Translation provider")
    DEFAULT_AVATAR_PROVIDER: str = Field(default="gpu_avatar", description="Default active Avatar provider")
    DEFAULT_IMAGE_PROVIDER: str = Field(default="mock", description="Default active Image provider")
    DEFAULT_VIDEO_PROVIDER: str = Field(default="mock", description="Default active Video provider")
    DEFAULT_MATTING_PROVIDER: str = Field(default="mock", description="Default active Matting provider")

    # Media Pipeline & External Binaries
    FFMPEG_PATH: str = Field(default="ffmpeg", description="Path to ffmpeg executable")
    FFPROBE_PATH: str = Field(default="ffprobe", description="Path to ffprobe executable")
    MEDIA_TEMP_DIR: Optional[str] = Field(default=None, description="Custom directory for worker scratch files")
    MEDIA_TIMEOUT_SECONDS: int = Field(default=300, ge=10, le=3600, description="Max execution duration per media subprocess")
    MAX_MEDIA_INPUT_SIZE_BYTES: int = Field(default=500 * 1024 * 1024, description="Max media input size (500MB)")

    # Video Generation & Duration Configuration
    MAX_VIDEO_DURATION_SECONDS: float = Field(
        default=3600.0,
        ge=10.0,
        le=14400.0,
        description="Sensible maximum video duration in seconds (configurable, default 1 hour)",
    )
    MIN_VIDEO_DURATION_SECONDS: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Minimum video duration in seconds",
    )

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100, description="SQLAlchemy connection pool max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, le=300, description="Connection acquisition timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60, description="Connection recycle interval in seconds")

    # Rate Limiting Settings
    RATE_LIMIT_AUTH_PER_MINUTE: int = Field(default=10, ge=1, description="Max auth requests per minute per IP")
    RATE_LIMIT_AI_JOB_PER_MINUTE: int = Field(default=20, ge=1, description="Max AI jobs created per minute per user")
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = Field(default=30, ge=1, description="Max upload intents per minute per user")
    RATE_LIMIT_API_PER_MINUTE: int = Field(default=120, ge=1, description="General API rate limit per minute per client")

    # Cookie & Session Security Settings
    COOKIE_SECURE: bool = Field(default=False, description="Set True in production for HTTPS-only cookies")
    COOKIE_SAMESITE: str = Field(default="lax", description="SameSite cookie policy: lax, strict, or none")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: str) -> str:
        """Ensure the connection URL uses the asyncpg driver."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql+psycopg://"):
                return v.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        """Return CORS origins normalized as a list of strings."""
        origins: List[str] = []
        if isinstance(self.CORS_ORIGINS, list):
            origins = [o.strip() for o in self.CORS_ORIGINS if o.strip()]
        elif isinstance(self.CORS_ORIGINS, str):
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        else:
            origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

        if self.FRONTEND_URL and self.FRONTEND_URL.strip():
            normalized_fe = self.FRONTEND_URL.strip().rstrip("/")
            if normalized_fe not in origins:
                origins.append(normalized_fe)

        return origins if origins else ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def s3_endpoint_resolved(self) -> str:
        return self.S3_ENDPOINT or self.MINIO_ENDPOINT

    @property
    def s3_access_key_resolved(self) -> str:
        return self.S3_ACCESS_KEY or self.MINIO_ACCESS_KEY

    @property
    def s3_secret_key_resolved(self) -> str:
        return self.S3_SECRET_KEY or self.MINIO_SECRET_KEY

    @property
    def s3_bucket_resolved(self) -> str:
        return self.S3_BUCKET or self.MINIO_BUCKET

    def validate_production_settings(self) -> None:
        """Fail-closed validation: ensure production environments never use unsafe defaults."""
        if self.APP_ENV.lower() != "production":
            return

        errors: List[str] = []

        if self.DEBUG:
            errors.append("DEBUG mode must be False in production.")

        insecure_jwt_defaults = {
            "dev_insecure_jwt_secret_key_for_local_testing_only_replace_in_prod",
            "secret",
            "changeme",
        }
        if self.JWT_SECRET_KEY in insecure_jwt_defaults or len(self.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY must be a cryptographically strong secret of at least 32 characters in production.")

        if "heyzen_dev_password" in self.DATABASE_URL:
            errors.append("DATABASE_URL contains the default insecure development password.")

        if self.s3_secret_key_resolved in ("heyzen_dev_password123", "minioadmin"):
            errors.append("S3/MinIO secret key contains default insecure development credentials.")

        if "*" in self.cors_origin_list:
            errors.append("Wildcard '*' CORS origin is not permitted in production with credentials enabled.")

        if errors:
            raise ValueError(f"PRODUCTION CONFIGURATION VALIDATION FAILED:\n" + "\n".join(f" - {e}" for e in errors))


@lru_cache
def get_settings() -> Settings:
    """Cached singleton instance of application settings."""
    return Settings()

