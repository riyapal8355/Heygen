"""Real Local CPU Neural Human Matting and Background Segmentation Provider.

Uses the Google MediaPipe Selfie Segmentation ONNX model (Apache-2.0, COMMERCIAL_SAFE)
via onnxruntime CPUExecutionProvider to extract high-accuracy alpha mattes from
avatar video streams and portrait images for multi-track timeline canvas compositing.
"""

import asyncio
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import onnxruntime as ort

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import MattingContractRequest, MattingContractResult
from app.ai.interfaces import MattingProvider, MattingResult
from app.core.config import get_settings
from app.core.exceptions import (
    AIInferenceException,
    AIModelIncompatibleException,
    AIRuntimeUnavailableException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)

# Default model cache location
DEFAULT_MEDIAPIPE_MATTING_PATH = os.path.join(
    "models_cache", "matting", "mediapipe", "model.onnx"
)
DEFAULT_MATTING_SHA256 = "3241ac4ad8aa35bdaf33946776db29f7c283a413aa0b0dacb9483594b4531aad"


class RealMediaPipeMattingProvider(MattingProvider):
    """Real ONNX-based CPU human portrait segmentation and alpha matte extraction provider."""

    provider_name: str = "mediapipe"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mediapipe",
        capability="matting",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["mp4", "png"],
        is_available=True,
        metadata={
            "engine": "ONNX Runtime (CPUExecutionProvider)",
            "model_family": "MediaPipe Selfie Segmentation",
            "license": "Apache-2.0",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
        },
    )

    def __init__(
        self,
        model_path: Optional[str] = None,
        threads: int = 4,
    ) -> None:
        self.model_path = model_path or os.getenv(
            "MEDIAPIPE_MATTING_MODEL_PATH", DEFAULT_MEDIAPIPE_MATTING_PATH
        )
        self.threads = threads
        self._session: Optional[ort.InferenceSession] = None
        self._lock = asyncio.Lock()

        # Telemetry
        self.model_name = "matting/mediapipe-selfie-cpu"
        self.provider_name = "mediapipe"
        self.load_time_ms: float = 0.0

    def _ensure_model_file_exists(self) -> str:
        """Verify that the model file exists on disk, raising structured errors in real mode."""
        resolved = Path(self.model_path)
        if not resolved.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent.parent
            resolved = backend_dir / self.model_path

        if not resolved.exists() or resolved.stat().st_size < 1000:
            raise AIModelIncompatibleException(
                message=(
                    f"MediaPipe Selfie Segmentation ONNX model not found at '{resolved}'. "
                    "Ensure the model is verified in the local cache."
                ),
                code="AI_MATTING_MODEL_NOT_FOUND",
                details={"model_path": str(resolved), "provider": self.provider_name},
            )
        return str(resolved)

    def _load_session_sync(self) -> ort.InferenceSession:
        """Synchronously initialize the ONNX Runtime inference session."""
        model_file = self._ensure_model_file_exists()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.threads
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        t0 = time.perf_counter()
        session = ort.InferenceSession(
            model_file,
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        self.load_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            "Loaded MediaPipe Selfie Segmentation ONNX model from '%s' in %.2f ms",
            model_file,
            self.load_time_ms,
        )
        return session

    async def _get_session(self) -> ort.InferenceSession:
        """Asynchronously load or retrieve the cached ONNX session."""
        if self._session is not None:
            return self._session

        async with self._lock:
            if self._session is None:
                self._session = await asyncio.to_thread(self._load_session_sync)
        return self._session

    def segment_frame_sync(
        self,
        session: ort.InferenceSession,
        frame_bgr: np.ndarray,
        threshold: float = 0.5,
        soft_matte: bool = True,
    ) -> np.ndarray:
        """Synchronously process a single BGR image frame and return a single-channel alpha mask [H, W] uint8 (0-255)."""
        orig_h, orig_w = frame_bgr.shape[:2]

        # 1. Preprocessing: BGR -> RGB, resize to 256x256, normalize to [0, 1] float32
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
        tensor = np.transpose(resized, (2, 0, 1)).astype(np.float32) / 255.0
        tensor = np.expand_dims(tensor, axis=0)  # [1, 3, 256, 256]

        # 2. Neural Inference
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        alphas_out = session.run([output_name], {input_name: tensor})[0]  # [1, 1, 256, 256]

        alpha_256 = alphas_out[0, 0]  # [256, 256] float32 in [0, 1]

        # 3. Postprocessing: resize back to original frame dimensions
        alpha_orig = cv2.resize(alpha_256, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        if soft_matte:
            # Soft continuous alpha map (0 to 255) with smooth anti-aliased edges
            alpha_uint8 = np.clip(alpha_orig * 255.0, 0, 255).astype(np.uint8)
            # Smoothly feather bottom 24px so presenter base dissolves seamlessly into canvas without edge artifacts
            fade_h = min(24, orig_h // 15)
            if fade_h > 0:
                ramp = np.linspace(1.0, 0.0, fade_h, dtype=np.float32)[:, None]
                alpha_uint8[-fade_h:, :] = np.clip(
                    alpha_uint8[-fade_h:, :].astype(np.float32) * ramp, 0, 255
                ).astype(np.uint8)
        else:
            # Binary mask based on threshold
            alpha_uint8 = np.where(alpha_orig >= threshold, 255, 0).astype(np.uint8)

        return alpha_uint8

    async def segment_frame(
        self,
        frame_bgr: np.ndarray,
        threshold: float = 0.5,
        soft_matte: bool = True,
    ) -> np.ndarray:
        """Asynchronously process a single BGR frame and return its alpha mask [H, W] uint8."""
        session = await self._get_session()
        return await asyncio.to_thread(
            self.segment_frame_sync, session, frame_bgr, threshold, soft_matte
        )

    def extract_video_matte_sync(
        self,
        session: ort.InferenceSession,
        input_video_path: Path,
        output_matte_video_path: Path,
        threshold: float = 0.5,
        soft_matte: bool = True,
    ) -> Dict[str, Any]:
        """Process an entire video file, writing an aligned greyscale alpha matte video (MP4) where pixel brightness = opacity."""
        cap = cv2.VideoCapture(str(input_video_path))
        if not cap.isOpened():
            raise AIInferenceException(
                message=f"Could not open input video '{input_video_path}' for neural matting.",
                code="MATTING_VIDEO_OPEN_FAILED",
            )

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        # Create output video writer for greyscale matte video
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_matte_video_path),
            fourcc,
            fps,
            (orig_w, orig_h),
            isColor=True,  # 3-channel greyscale for broad FFmpeg compatibility
        )

        frames_processed = 0
        t0 = time.perf_counter()

        try:
            while True:
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    break

                alpha_uint8 = self.segment_frame_sync(
                    session, frame_bgr, threshold=threshold, soft_matte=soft_matte
                )
                # Convert 1-channel alpha to 3-channel greyscale frame
                matte_3ch = cv2.cvtColor(alpha_uint8, cv2.COLOR_GRAY2BGR)
                writer.write(matte_3ch)
                frames_processed += 1
        finally:
            cap.release()
            writer.release()

        total_time = time.perf_counter() - t0
        throughput_fps = round(frames_processed / max(0.001, total_time), 2)

        return {
            "width": orig_w,
            "height": orig_h,
            "fps": fps,
            "frame_count": frames_processed,
            "latency_seconds": round(total_time, 3),
            "throughput_fps": throughput_fps,
        }

    async def extract_matte(
        self,
        video_storage_key: str,
        output_format: str = "matte_mask",
        threshold: float = 0.5,
    ) -> MattingResult:
        """Extract foreground human alpha matte from storage video, uploading the result to MinIO."""
        storage = get_storage_provider()
        if not storage.object_exists(video_storage_key):
            raise NotFoundException(
                message=f"Source video '{video_storage_key}' not found in storage.",
                code="MATTING_SOURCE_NOT_FOUND",
            )

        session = await self._get_session()

        with tempfile.TemporaryDirectory(prefix="matting_") as tmp_dir:
            tmp_in = Path(tmp_dir) / "source_input.mp4"
            tmp_out = Path(tmp_dir) / "alpha_matte.mp4"

            # Download source bytes to temp file
            source_bytes = await storage.get_object(video_storage_key)
            tmp_in.write_bytes(source_bytes)

            metrics = await asyncio.to_thread(
                self.extract_video_matte_sync,
                session,
                tmp_in,
                tmp_out,
                threshold,
                True,
            )

            # Upload generated alpha matte video to storage
            matte_bytes = tmp_out.read_bytes()
            out_key = f"mattes/{uuid.uuid4().hex[:12]}_alpha_matte.mp4"
            await storage.put_object(out_key, matte_bytes, content_type="video/mp4")

            duration = round(metrics["frame_count"] / max(1.0, metrics["fps"]), 2)

            return MattingResult(
                alpha_storage_key=out_key,
                width=metrics["width"],
                height=metrics["height"],
                frame_count=metrics["frame_count"],
                fps=metrics["fps"],
                duration_seconds=duration,
                metrics={
                    "model_name": self.model_name,
                    "provider_name": self.provider_name,
                    "latency_seconds": metrics["latency_seconds"],
                    "throughput_fps": metrics["throughput_fps"],
                },
            )

    async def segment(
        self,
        request: MattingContractRequest,
    ) -> MattingContractResult:
        """Execute human matting using strongly typed execution contract."""
        storage_key = request.media_asset.storage_key
        if not storage_key:
            raise ValueError("MattingContractRequest must specify media_asset.storage_key.")

        result = await self.extract_matte(
            video_storage_key=storage_key,
            output_format=request.output_format,
            threshold=request.threshold,
        )

        return MattingContractResult(
            status="succeeded",
            output_storage_key=result.alpha_storage_key,
            duration_seconds=result.duration_seconds,
            frame_count=result.frame_count,
            width=result.width,
            height=result.height,
            fps=result.fps,
            processing_latency=result.metrics.get("latency_seconds", 0.0),
            fps_throughput=result.metrics.get("throughput_fps", 0.0),
            metrics=result.metrics,
        )
