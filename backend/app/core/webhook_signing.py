"""HMAC-SHA256 webhook payload signing, verification, and replay protection."""

import hashlib
import hmac
import time
from typing import Optional, Tuple


def generate_webhook_signature(secret: str, timestamp: str, raw_payload: str) -> str:
    """Generate canonical HMAC-SHA256 signature for a webhook payload.

    Canonical message format: timestamp + "." + raw_payload
    Returns: "v1=" + hex_signature
    """
    canonical_message = f"{timestamp}.{raw_payload}"
    mac = hmac.new(
        secret.encode("utf-8"),
        canonical_message.encode("utf-8"),
        hashlib.sha256,
    )
    return f"v1={mac.hexdigest()}"


def verify_webhook_signature(
    secret: str,
    raw_payload: str,
    header_timestamp: str,
    header_signature: str,
    tolerance_seconds: int = 300,
) -> Tuple[bool, Optional[str]]:
    """Verify an incoming webhook HMAC-SHA256 signature with replay protection.

    Args:
        secret: Shared webhook secret key.
        raw_payload: Exact unmodified request body string.
        header_timestamp: Value from X-HeyZen-Timestamp header (UTC epoch string).
        header_signature: Value from X-HeyZen-Signature header (e.g. "v1=...").
        tolerance_seconds: Maximum allowed clock divergence (default 300s).

    Returns:
        (is_valid, error_reason)
    """
    if not header_timestamp:
        return False, "Missing timestamp header"
    if not header_signature:
        return False, "Missing signature header"

    # 1. Validate timestamp format and evaluate replay tolerance
    try:
        ts_int = int(header_timestamp)
    except ValueError:
        return False, "Malformed timestamp header"

    current_time = int(time.time())
    if current_time - ts_int > tolerance_seconds:
        return False, f"Timestamp is too old (exceeds {tolerance_seconds}s replay tolerance)"
    if ts_int - current_time > 60:
        return False, "Timestamp is too far in the future"

    # 2. Extract signature format
    if not header_signature.startswith("v1="):
        return False, "Unsupported signature scheme (expected 'v1=...')"

    expected_sig = generate_webhook_signature(secret, header_timestamp, raw_payload)

    # 3. Constant-time comparison
    if not hmac.compare_digest(expected_sig, header_signature):
        return False, "Signature mismatch"

    return True, None
