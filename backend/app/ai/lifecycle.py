"""Model Lifecycle and Security Controls.

Manages model lifecycle stages:
    discover -> download -> verify -> cache -> load -> health check -> inference -> unload
Enforces strict security policies preventing path traversal, checksum mismatches,
untrusted downloads, and arbitrary executable code execution.
"""

import hashlib
import os
from typing import Any, Dict, Optional
from app.ai.model_registry import ModelDescriptor, ModelHealthStatus, ModelInstallStatus
from app.ai.runtimes import AIRuntime
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIModelSecurityException,
    NotFoundException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def resolve_safe_cache_path(base_dir: str, subpath: str) -> str:
    """Resolve subpath securely within base_dir, strictly blocking directory traversal attacks.

    Raises:
        AIModelSecurityException: If resolved path escapes the base_dir root.
    """
    abs_base = os.path.abspath(os.path.normpath(base_dir))
    target = os.path.abspath(os.path.normpath(os.path.join(abs_base, subpath)))

    # Verify that target starts strictly with abs_base
    try:
        common = os.path.commonpath([abs_base, target])
    except ValueError:
        # Happens on Windows if paths are on different drives
        raise AIModelSecurityException(
            message=f"Path traversal detected: path '{subpath}' resides on a different drive than cache root.",
            code="AI_PATH_TRAVERSAL_DETECTED",
        )

    if common != abs_base:
        raise AIModelSecurityException(
            message=f"Path traversal detected: path '{subpath}' attempts to escape model cache root.",
            code="AI_PATH_TRAVERSAL_DETECTED",
            details={"base_dir": abs_base, "target": target},
        )

    return target


def compute_file_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hex digest for an on-disk model artifact."""
    if not os.path.isfile(file_path):
        raise NotFoundException(
            message=f"File not found for checksum calculation: {file_path}",
            code="FILE_NOT_FOUND",
        )
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_model_checksum(file_path: str, expected_sha256: str) -> bool:
    """Verify artifact file integrity against expected SHA-256 hash.

    Raises:
        AIModelSecurityException: If hashes do not match.
    """
    actual_hash = compute_file_sha256(file_path)
    clean_expected = expected_sha256.strip().lower()
    if actual_hash.lower() != clean_expected:
        raise AIModelSecurityException(
            message=f"Model artifact checksum mismatch for '{os.path.basename(file_path)}'.",
            code="AI_CHECKSUM_MISMATCH",
            details={
                "file_path": file_path,
                "expected_sha256": clean_expected,
                "actual_sha256": actual_hash,
            },
        )
    return True


class ModelLifecycleManager:
    """Orchestrates model caching, verification, loading, and unload lifecycle."""

    def __init__(self, cache_root: Optional[str] = None) -> None:
        settings = get_settings()
        self.cache_root = os.path.abspath(cache_root or settings.AI_MODEL_CACHE_DIR)
        self._loaded_models: Dict[str, Any] = {}

    def ensure_cache_dir(self) -> str:
        """Create and return verified safe model cache root directory."""
        os.makedirs(self.cache_root, exist_ok=True)
        return self.cache_root

    def get_model_path(self, model_id: str) -> str:
        """Resolve safe local path for a model ID inside cache root."""
        # Sanitize model_id to prevent relative traversal components
        safe_rel = model_id.strip().replace("..", "").lstrip("/\\")
        return resolve_safe_cache_path(self.cache_root, safe_rel)

    def verify_artifact(self, descriptor: ModelDescriptor) -> bool:
        """Verify model file existence and SHA-256 integrity if specified."""
        target_path = descriptor.cache_path or self.get_model_path(descriptor.model_id)
        if not os.path.exists(target_path):
            descriptor.installation_status = ModelInstallStatus.NOT_INSTALLED
            return False

        settings = get_settings()
        if settings.AI_VERIFY_CHECKSUMS and descriptor.checksum_sha256:
            # If target_path is a file, check directly; if dir, check weights file inside
            check_file = target_path
            if os.path.isdir(target_path):
                candidates = [
                    os.path.join(target_path, "model.onnx"),
                    os.path.join(target_path, "model.safetensors"),
                    os.path.join(target_path, "model.bin"),
                ]
                found = next((c for c in candidates if os.path.exists(c)), None)
                if found:
                    check_file = found
            if os.path.isfile(check_file):
                verify_model_checksum(check_file, descriptor.checksum_sha256)

        descriptor.installation_status = ModelInstallStatus.VERIFIED
        descriptor.health_status = ModelHealthStatus.HEALTHY
        return True

    def load_model(self, descriptor: ModelDescriptor, runtime: AIRuntime) -> Any:
        """Load and cache model instance in memory, validating runtime compatibility."""
        model_id = descriptor.model_id
        if model_id in self._loaded_models:
            return self._loaded_models[model_id]

        # Verify runtime compatibility
        is_compat, reason = runtime.check_compatibility(descriptor)
        if not is_compat:
            raise AIModelIncompatibleException(
                message=f"Cannot load model '{model_id}' on runtime '{runtime.runtime_id}': {reason}",
                code="AI_MODEL_INCOMPATIBLE",
                details={"model_id": model_id, "runtime_id": runtime.runtime_id, "reason": reason},
            )

        # Enforce download policy
        settings = get_settings()
        target_path = descriptor.cache_path or self.get_model_path(descriptor.model_id)
        if not os.path.exists(target_path):
            if not settings.AI_ALLOW_AUTO_DOWNLOAD and descriptor.provider != "mock":
                raise AIModelSecurityException(
                    message=(
                        f"Model '{model_id}' is not installed locally. Automatic download during "
                        f"request execution is prohibited by security policy (AI_ALLOW_AUTO_DOWNLOAD=False). "
                        f"Install model explicitly before invoking inference."
                    ),
                    code="AI_AUTO_DOWNLOAD_PROHIBITED",
                    details={"model_id": model_id},
                )

        logger.info("Loaded model '%s' into runtime '%s'", model_id, runtime.runtime_id)
        # Store active instance reference (for Step 1 mock/built-in descriptor handle)
        self._loaded_models[model_id] = descriptor
        descriptor.installation_status = ModelInstallStatus.INSTALLED
        descriptor.health_status = ModelHealthStatus.HEALTHY
        return descriptor

    def unload_model(self, model_id: str) -> bool:
        """Evict model from active memory."""
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            logger.info("Unloaded model '%s' from active memory", model_id)
            return True
        return False

    def is_loaded(self, model_id: str) -> bool:
        """Check if model is currently active in memory."""
        return model_id in self._loaded_models

    def clear_all(self) -> None:
        """Unload all active models."""
        self._loaded_models.clear()

    def install_piper_voice(
        self,
        voice_id: str = "en_US-lessac-medium",
        onnx_path: Optional[str] = None,
        config_path: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> str:
        """Register and verify a local Piper voice model in cache root.

        Copies or validates the presence of the ONNX model and config in safe cache location:
        AI_MODEL_CACHE_DIR/tts/piper/<voice_id>/<voice_id>.onnx
        Validates checksum if expected_sha256 is provided.
        """
        dest_dir = resolve_safe_cache_path(self.cache_root, os.path.join("tts", "piper", voice_id))
        os.makedirs(dest_dir, exist_ok=True)
        dest_onnx = os.path.join(dest_dir, f"{voice_id}.onnx")
        dest_json = os.path.join(dest_dir, f"{voice_id}.onnx.json")

        if onnx_path and os.path.isfile(onnx_path) and os.path.abspath(onnx_path) != os.path.abspath(dest_onnx):
            import shutil
            shutil.copy2(onnx_path, dest_onnx)
        if config_path and os.path.isfile(config_path) and os.path.abspath(config_path) != os.path.abspath(dest_json):
            import shutil
            shutil.copy2(config_path, dest_json)

        if not os.path.isfile(dest_onnx):
            raise NotFoundException(
                message=f"Piper voice ONNX file not found at {dest_onnx}",
                code="AI_MODEL_NOT_FOUND",
                details={"voice_id": voice_id, "dest_onnx": dest_onnx},
            )

        settings = get_settings()
        if expected_sha256 and settings.AI_VERIFY_CHECKSUMS:
            verify_model_checksum(dest_onnx, expected_sha256)

        logger.info("Piper voice model '%s' successfully installed and verified at '%s'", voice_id, dest_onnx)
        return dest_onnx

    def install_whisper_model(
        self,
        model_id: str = "tiny",
        model_bin_path: Optional[str] = None,
        config_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        vocabulary_path: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> str:
        """Register and verify a local Whisper CTranslate2 model in cache root.

        Copies or validates the presence of model.bin, config.json, tokenizer.json, vocabulary.txt
        in safe cache location: AI_MODEL_CACHE_DIR/asr/whisper/<model_id>/
        Validates checksum of model.bin if expected_sha256 is provided.
        """
        dest_dir = resolve_safe_cache_path(self.cache_root, os.path.join("asr", "whisper", model_id))
        os.makedirs(dest_dir, exist_ok=True)
        dest_bin = os.path.join(dest_dir, "model.bin")

        import shutil
        file_mappings = [
            (model_bin_path, "model.bin"),
            (config_path, "config.json"),
            (tokenizer_path, "tokenizer.json"),
            (vocabulary_path, "vocabulary.txt"),
        ]
        for src_path, target_name in file_mappings:
            if src_path and os.path.isfile(src_path):
                target_dest = os.path.join(dest_dir, target_name)
                if os.path.abspath(src_path) != os.path.abspath(target_dest):
                    shutil.copy2(src_path, target_dest)

        if not os.path.isfile(dest_bin):
            raise NotFoundException(
                message=f"Whisper model.bin file not found at {dest_bin}",
                code="AI_MODEL_NOT_FOUND",
                details={"model_id": model_id, "dest_bin": dest_bin},
            )

        settings = get_settings()
        if expected_sha256 and settings.AI_VERIFY_CHECKSUMS:
            verify_model_checksum(dest_bin, expected_sha256)

        logger.info("Whisper model '%s' successfully installed and verified at '%s'", model_id, dest_dir)
        return dest_dir

    def install_wav2lip_model(
        self,
        model_name: str = "wav2lip",
        onnx_path: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> str:
        """Register and verify a local Wav2Lip ONNX model in cache root.

        Copies or validates the presence of the ONNX model in safe cache location:
        AI_MODEL_CACHE_DIR/avatar/wav2lip/<model_name>.onnx
        Validates checksum if expected_sha256 is provided.
        """
        dest_dir = resolve_safe_cache_path(self.cache_root, os.path.join("avatar", "wav2lip"))
        os.makedirs(dest_dir, exist_ok=True)
        dest_onnx = os.path.join(dest_dir, f"{model_name}.onnx")

        if onnx_path and os.path.isfile(onnx_path) and os.path.abspath(onnx_path) != os.path.abspath(dest_onnx):
            import shutil
            shutil.copy2(onnx_path, dest_onnx)

        if not os.path.isfile(dest_onnx):
            raise NotFoundException(
                message=f"Wav2Lip ONNX model file not found at {dest_onnx}",
                code="AI_MODEL_NOT_FOUND",
                details={"model_name": model_name, "dest_onnx": dest_onnx},
            )

        settings = get_settings()
        if expected_sha256 and settings.AI_VERIFY_CHECKSUMS:
            verify_model_checksum(dest_onnx, expected_sha256)

        logger.info("Wav2Lip ONNX model '%s' successfully installed and verified at '%s'", model_name, dest_onnx)
        return dest_onnx


# Global lifecycle manager singleton
_lifecycle_manager_instance: Optional[ModelLifecycleManager] = None


def get_lifecycle_manager() -> ModelLifecycleManager:
    """Retrieve global ModelLifecycleManager singleton."""
    global _lifecycle_manager_instance
    if _lifecycle_manager_instance is None:
        _lifecycle_manager_instance = ModelLifecycleManager()
    return _lifecycle_manager_instance
