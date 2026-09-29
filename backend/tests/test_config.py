"""Tests for configuration loading and validation."""

from app.core.config import Settings, get_settings


def test_settings_load_defaults():
    """Verify default settings values and properties."""
    settings = get_settings()
    assert settings.APP_NAME is not None
    assert settings.APP_VERSION == "0.1.0"
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert settings.REDIS_URL.startswith("redis://")
    assert len(settings.cors_origin_list) > 0
    assert "http://localhost:3000" in settings.cors_origin_list


def test_s3_endpoint_resolution():
    """Verify S3 endpoint resolution with fallback."""
    settings = get_settings()
    assert settings.s3_endpoint_resolved is not None
    assert settings.s3_bucket_resolved is not None
    assert settings.s3_access_key_resolved is not None
    assert settings.s3_secret_key_resolved is not None


def test_cors_origin_parsing():
    """Verify parsing comma-separated origins."""
    s = Settings(CORS_ORIGINS="http://localhost:3000, http://test.heyzen.ai")
    assert s.cors_origin_list == ["http://localhost:3000", "http://test.heyzen.ai"]
