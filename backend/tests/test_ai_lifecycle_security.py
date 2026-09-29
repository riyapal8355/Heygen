"""Security and lifecycle validation tests (traversal, checksums, download policies)."""

import os
import tempfile
import pytest

from app.ai.lifecycle import (
    ModelLifecycleManager,
    compute_file_sha256,
    resolve_safe_cache_path,
    verify_model_checksum,
)
from app.ai.model_registry import ModelDescriptor
from app.ai.runtimes import LocalCPURuntime
from app.core.exceptions import AIModelSecurityException


def test_path_traversal_detection():
    """Verify that path traversal attempts outside model cache root are strictly blocked."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Valid safe subpath
        safe_path = resolve_safe_cache_path(tmp_dir, "tts/piper-cpu/model.onnx")
        assert safe_path.startswith(tmp_dir)

        # Directory traversal attacks
        with pytest.raises(AIModelSecurityException) as exc_info1:
            resolve_safe_cache_path(tmp_dir, "../../etc/passwd")
        assert exc_info1.value.code == "AI_PATH_TRAVERSAL_DETECTED"

        with pytest.raises(AIModelSecurityException) as exc_info2:
            resolve_safe_cache_path(tmp_dir, r"..\..\Windows\System32\cmd.exe")
        assert exc_info2.value.code == "AI_PATH_TRAVERSAL_DETECTED"


def test_checksum_verification_valid_and_corrupt():
    """Verify SHA-256 checksum validation passes on valid file and rejects tampered file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "weights.bin")
        content = b"heyzen-verified-model-binary-content-12345"
        with open(test_file, "wb") as f:
            f.write(content)

        actual_sha256 = compute_file_sha256(test_file)
        assert len(actual_sha256) == 64

        # Valid checksum matches
        assert verify_model_checksum(test_file, actual_sha256) is True

        # Mismatched/corrupt checksum raises security violation
        wrong_hash = "0" * 64
        with pytest.raises(AIModelSecurityException) as exc_info:
            verify_model_checksum(test_file, wrong_hash)
        assert exc_info.value.code == "AI_CHECKSUM_MISMATCH"


def test_auto_download_policy_enforcement():
    """Verify that auto-downloading large uninstalled models during inference is blocked."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = ModelLifecycleManager(cache_root=tmp_dir)
        runtime = LocalCPURuntime()

        uninstalled_model = ModelDescriptor(
            model_id="tts/uninstalled-piper",
            name="Uninstalled Piper",
            provider="piper",  # real non-mock provider
            capability="tts",
            supported_devices=["cpu"],
            requires_gpu=False,
            cache_path=os.path.join(tmp_dir, "missing_model.onnx"),
        )

        with pytest.raises(AIModelSecurityException) as exc_info:
            mgr.load_model(uninstalled_model, runtime)
        assert exc_info.value.code == "AI_AUTO_DOWNLOAD_PROHIBITED"


def test_model_load_unload_lifecycle():
    """Verify model loading, query, and eviction in ModelLifecycleManager."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = ModelLifecycleManager(cache_root=tmp_dir)
        runtime = LocalCPURuntime()

        mock_model = ModelDescriptor(
            model_id="tts/mock-tts-cycle",
            name="Mock Cycle",
            provider="mock",
            capability="tts",
            supported_devices=["cpu"],
            requires_gpu=False,
        )

        # Load
        loaded = mgr.load_model(mock_model, runtime)
        assert loaded is not None
        assert mgr.is_loaded("tts/mock-tts-cycle") is True

        # Unload
        unloaded = mgr.unload_model("tts/mock-tts-cycle")
        assert unloaded is True
        assert mgr.is_loaded("tts/mock-tts-cycle") is False
