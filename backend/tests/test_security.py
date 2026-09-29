"""Tests for Argon2id password hashing and JWT encoding/decoding."""

from datetime import timedelta
import pytest
import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hashing_and_verification():
    """Verify Argon2id hash generation and strict verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Hash must be an Argon2id format string
    assert hashed.startswith("$argon2id$")
    assert hashed != password

    # Correct password succeeds
    assert verify_password(password, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False


def test_empty_password_raises():
    """Verify empty password raises ValueError."""
    with pytest.raises(ValueError):
        hash_password("")


def test_jwt_access_token_lifecycle():
    """Verify JWT access token creation and decoding."""
    subject_id = "018e1540-7e12-7000-84a1-b40b1275d8aa"
    claims = {"role": "admin", "workspace_id": "ws-123"}
    token = create_access_token(subject=subject_id, claims=claims)

    decoded = decode_token(token)
    assert decoded["sub"] == subject_id
    assert decoded["type"] == "access"
    assert decoded["role"] == "admin"
    assert decoded["workspace_id"] == "ws-123"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_refresh_token_lifecycle():
    """Verify JWT refresh token creation and decoding."""
    subject_id = "018e1540-7e12-7000-84a1-b40b1275d8aa"
    token = create_refresh_token(subject=subject_id)

    decoded = decode_token(token)
    assert decoded["sub"] == subject_id
    assert decoded["type"] == "refresh"


def test_expired_jwt_raises():
    """Verify expired token raises ExpiredSignatureError."""
    token = create_access_token(
        subject="user-123",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
