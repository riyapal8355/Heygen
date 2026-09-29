#!/usr/bin/env python3
"""Deterministic GPU Model Provisioning and Artifact Verification CLI.

Downloads, validates, verifies byte-size and SHA-256 integrity, and stages approved
GPU model artifacts into persistent model cache (/app/models_cache or AI_MODEL_CACHE_DIR).

Fails closed on:
- BLOCKED, NON_COMMERCIAL, RESEARCH_ONLY, UNKNOWN artifacts
- Path traversal or unsafe paths
- Size mismatches
- Checksum mismatches
- Interrupted or partial downloads
"""

import argparse
import os
import shutil
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.gpu_manifest import (
    CommercialStatus,
    GPU_MODEL_MANIFEST,
    GPUArtifactManifestEntry,
    assert_artifact_not_blocked,
    get_gpu_manifest_entry,
)
from app.ai.lifecycle import compute_file_sha256, resolve_safe_cache_path
from app.core.config import get_settings
from app.core.exceptions import AIModelSecurityException
from app.core.logging import get_logger

logger = get_logger("provision_gpu_models")


def get_target_cache_dir(custom_dir: Optional[str] = None) -> str:
    """Resolve absolute path to model cache root."""
    if custom_dir:
        return os.path.abspath(os.path.normpath(custom_dir))
    settings = get_settings()
    return os.path.abspath(os.path.normpath(settings.AI_MODEL_CACHE_DIR))


def verify_staged_artifact(
    entry: GPUArtifactManifestEntry,
    cache_root: str,
) -> Tuple[bool, str]:
    """Verify an already provisioned artifact in the local cache root.

    Returns:
        (is_valid, reason)
    """
    # 1. Blocked check
    try:
        assert_artifact_not_blocked(entry.model_id)
    except AIModelSecurityException as exc:
        return False, f"SECURITY_BLOCKED: {exc.message}"

    # 2. Status check
    if entry.commercial_status in (
        CommercialStatus.BLOCKED,
        CommercialStatus.NON_COMMERCIAL,
        CommercialStatus.RESEARCH_ONLY,
        CommercialStatus.UNKNOWN,
    ):
        return False, f"STATUS_REJECTED: Commercial status is {entry.commercial_status.value}"

    # 3. Path safety check
    try:
        final_path = resolve_safe_cache_path(cache_root, entry.relative_path)
    except Exception as exc:
        return False, f"PATH_TRAVERSAL_DETECTED: {exc}"

    if not os.path.isfile(final_path):
        return False, f"MISSING: File not found at {final_path}"

    # 4. Byte size check
    actual_size = os.path.getsize(final_path)
    if entry.expected_size_bytes > 0:
        # Require exact match or minimum bound within expected tolerance
        if actual_size != entry.expected_size_bytes:
            return False, f"SIZE_MISMATCH: Expected {entry.expected_size_bytes} bytes, found {actual_size} bytes"

    # 5. Checksum verification
    if entry.expected_sha256:
        try:
            actual_sha = compute_file_sha256(final_path)
            if actual_sha.lower() != entry.expected_sha256.strip().lower():
                return False, f"CHECKSUM_MISMATCH: Expected {entry.expected_sha256}, got {actual_sha}"
        except Exception as exc:
            return False, f"CHECKSUM_ERROR: {exc}"

    return True, f"READY: Verified at {final_path}"


def download_and_stage_artifact(
    entry: GPUArtifactManifestEntry,
    cache_root: str,
    overwrite: bool = False,
) -> Tuple[bool, str]:
    """Download, verify, and atomically stage an artifact into the persistent cache.

    Follows atomic staging:
    download -> temporary file -> verify size -> verify SHA256 -> atomic rename -> READY
    """
    # 1. Blocked check
    try:
        assert_artifact_not_blocked(entry.model_id)
    except AIModelSecurityException as exc:
        return False, f"SECURITY_BLOCKED: {exc.message}"

    if entry.commercial_status in (
        CommercialStatus.BLOCKED,
        CommercialStatus.NON_COMMERCIAL,
        CommercialStatus.RESEARCH_ONLY,
        CommercialStatus.UNKNOWN,
    ):
        return False, f"STATUS_REJECTED: Model '{entry.model_id}' status is {entry.commercial_status.value}"

    # 2. Path verification
    final_path = resolve_safe_cache_path(cache_root, entry.relative_path)
    target_dir = os.path.dirname(final_path)
    os.makedirs(target_dir, exist_ok=True)

    # 3. Check if already provisioned
    if os.path.isfile(final_path) and not overwrite:
        valid, msg = verify_staged_artifact(entry, cache_root)
        if valid:
            logger.info("Artifact '%s' already verified and present at '%s'.", entry.model_id, final_path)
            return True, f"ALREADY_VERIFIED: {final_path}"

    if not entry.provenance or not entry.provenance.startswith("http"):
        return False, f"PROVENANCE_INVALID: No valid HTTP URL for artifact '{entry.model_id}'"

    # 4. Atomic temporary file download
    tmp_path = f"{final_path}.download.{os.getpid()}.tmp"
    logger.info("Downloading '%s' from '%s' to '%s'...", entry.model_id, entry.provenance, tmp_path)

    try:
        import httpx

        with httpx.stream("GET", entry.provenance, follow_redirects=True, timeout=300.0) as resp:
            if resp.status_code != 200:
                return False, f"DOWNLOAD_FAILED: HTTP status {resp.status_code} from {entry.provenance}"

            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1048576):
                    f.write(chunk)

        # 5. Verify byte size
        actual_size = os.path.getsize(tmp_path)
        if entry.expected_size_bytes > 0 and actual_size != entry.expected_size_bytes:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False, f"SIZE_INVALID: Expected {entry.expected_size_bytes} bytes, received {actual_size} bytes"

        # 6. Verify SHA256 checksum
        if entry.expected_sha256:
            actual_sha = compute_file_sha256(tmp_path)
            if actual_sha.lower() != entry.expected_sha256.strip().lower():
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return False, f"CHECKSUM_INVALID: Expected {entry.expected_sha256}, calculated {actual_sha}"

        # 7. Atomic rename
        os.replace(tmp_path, final_path)
        logger.info("Successfully provisioned and verified '%s' at '%s'.", entry.model_id, final_path)
        return True, f"READY: {final_path}"

    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        logger.error("Failed to provision '%s': %s", entry.model_id, exc)
        return False, f"ERROR: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="HeyZen GPU Model Provisioning & Integrity Verification CLI")
    parser.add_argument("--model-id", type=str, help="Specific model ID to provision or verify")
    parser.add_argument("--all", action="store_true", help="Provision all approved GPU models")
    parser.add_argument("--verify-only", action="store_true", help="Verify integrity of local artifacts without downloading")
    parser.add_argument("--cache-dir", type=str, default=None, help="Custom models cache directory")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing cached files")

    args = parser.parse_args()
    cache_root = get_target_cache_dir(args.cache_dir)
    os.makedirs(cache_root, exist_ok=True)

    targets: List[GPUArtifactManifestEntry] = []
    if args.model_id:
        entry = get_gpu_manifest_entry(args.model_id)
        if not entry:
            print(f"ERROR: Model ID '{args.model_id}' not found in GPU catalog manifest.", file=sys.stderr)
            return 1
        targets.append(entry)
    elif args.all:
        for entry in GPU_MODEL_MANIFEST.values():
            if entry.commercial_status in (CommercialStatus.APPROVED, CommercialStatus.CONDITIONAL):
                targets.append(entry)
    else:
        parser.print_help()
        return 1

    overall_success = True
    print(f"--- HeyZen GPU Model Provisioning [Cache: {cache_root}] ---")

    for entry in targets:
        print(f"\nProcessing [{entry.model_id}] (Status: {entry.commercial_status.value}, License: {entry.license})")

        # Blocked assertion test
        try:
            assert_artifact_not_blocked(entry.model_id)
        except AIModelSecurityException as sec_exc:
            print(f"  [FAIL] Rejected by policy: {sec_exc.message}", file=sys.stderr)
            overall_success = False
            continue

        if args.verify_only:
            valid, reason = verify_staged_artifact(entry, cache_root)
            status_tag = "PASS" if valid else "FAIL"
            print(f"  [{status_tag}] {reason}")
            if not valid:
                overall_success = False
        else:
            success, reason = download_and_stage_artifact(entry, cache_root, overwrite=args.overwrite)
            status_tag = "READY" if success else "FAIL"
            print(f"  [{status_tag}] {reason}")
            if not success:
                overall_success = False

    print("\n--- Summary ---")
    if overall_success:
        print("All target GPU models verified / provisioned successfully.")
        return 0
    else:
        print("One or more GPU models failed verification or provisioning.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
