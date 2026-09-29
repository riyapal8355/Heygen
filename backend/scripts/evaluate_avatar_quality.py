"""Avatar Quality Evaluation and Standalone Gate Script.

Conforms strictly to the GPU-Ready Neural Avatar Architecture specification:
- Truthful hardware capability auditing.
- Never creates fake or placeholder MP4 files for unexecuted neural models.
- On CPU-only hosts:
    - LivePortrait: GPU_REQUIRED (no MP4)
    - MuseTalk 1.5: GPU_REQUIRED (no MP4)
    - Hallo2:       GPU_REQUIRED (no MP4)
    - Wav2Lip:      EXECUTED (annie_wav2lip_fallback.mp4)
- Produces:
    - test-results/avatar_quality/manifest.json
    - test-results/avatar_quality/execution.json
    - test-results/avatar_quality/source.png
    - test-results/avatar_quality/driving.mp4
    - test-results/avatar_quality/annie_wav2lip_fallback.mp4
    - test-results/avatar_quality/fallback_contact_sheet.jpg
    - test-results/avatar_quality/face_closeups.jpg
    - test-results/avatar_quality/mouth_closeups.jpg
    - test-results/avatar_quality/eye_closeups.jpg
    - test-results/avatar_quality/comparison_available.jpg
    - test-results/avatar_quality/comparison_ablation.jpg
"""

import asyncio
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import cv2
import numpy as np

from app.ai.adapters.hallo2 import Hallo2Adapter
from app.ai.adapters.liveportrait import LivePortraitAdapter, LivePortraitMotionOptions
from app.ai.adapters.musetalk import MuseTalkAvatarProvider
from app.ai.adapters.piper import PiperTTSProvider
from app.ai.adapters.wav2lip import LegacyDelaunayAvatarProvider, Wav2LipONNXAvatarProvider
from app.ai.hardware import detect_hardware, get_neural_avatar_hardware_status
from app.ai.model_registry import discover_model_state
from app.ai.providers.gpu_avatar_provider import GPUAvatarProvider, GPUAvatarProviderMode
from app.core.exceptions import AIRuntimeUnavailableException
from app.core.logging import get_logger
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService

logger = get_logger(__name__)

REPO_ROOT = BACKEND_ROOT.parent
OUTPUT_DIR_ROOT = REPO_ROOT / "test-results" / "avatar_quality"
OUTPUT_DIR_BACKEND = BACKEND_ROOT / "test-results" / "avatar_quality"

ANNIE_SCRIPT = (
    "Welcome to HeyZen. We build the future of autonomous neural video creation "
    "with studio-grade audio synthesis and precision facial synchronization."
)


def compute_sha256(filepath: Path) -> str:
    """Compute hex SHA256 of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def remove_misleading_artifacts(dirs: list[Path]) -> None:
    """Purge false model outputs and mislabeled files."""
    misleading_filenames = [
        "liveportrait.mp4",
        "musetalk.mp4",
        "hallo2.mp4",
        "final_neural_avatar.mp4",
        "annie_neural_avatar.mp4",
        "daniel_neural_avatar.mp4",
        "comparison.jpg",
    ]
    for d in dirs:
        if not d.exists():
            continue
        for name in misleading_filenames:
            target = d / name
            if target.exists():
                try:
                    target.unlink()
                    print(f" -> Removed misleading artifact: {target}")
                except Exception as exc:
                    print(f" -> Failed to remove {target}: {exc}")


async def synthesize_speech(text: str, voice_id: str, out_wav: Path) -> Path:
    """Generate high-clarity Piper TTS audio."""
    tts = PiperTTSProvider()
    res = await tts.synthesize_speech(text=text, voice_id=voice_id)
    wav_bytes = res.audio_bytes if hasattr(res, "audio_bytes") else (res[0] if isinstance(res, tuple) else res)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    out_wav.write_bytes(wav_bytes)
    return out_wav


def extract_frame_at_sec(video_path: Path, sec: float) -> np.ndarray:
    """Extract RGB frame at specified timestamp."""
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000.0)
    ret, frame_bgr = cap.read()
    cap.release()
    if not ret or frame_bgr is None:
        raise ValueError(f"Could not read frame at {sec}s from {video_path}")
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def build_contact_sheet(video_path: Path, output_image: Path, num_frames: int = 12) -> None:
    """Create a 3x4 contact sheet across the video duration."""
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()

    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = []

    cap = cv2.VideoCapture(str(video_path))
    for idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        if idx in indices:
            t_sec = idx / fps
            cv2.putText(
                frame,
                f"T={t_sec:.1f}s (F{idx}) - CPU Fallback",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            frames.append(frame)
    cap.release()

    cols = 4
    rows = 3
    tw, th = 320, 320
    sheet = np.zeros((rows * th, cols * tw, 3), dtype=np.uint8)

    for i, f in enumerate(frames[:num_frames]):
        r = i // cols
        c = i % cols
        thumb = cv2.resize(f, (tw, th))
        sheet[r * th : (r + 1) * th, c * tw : (c + 1) * tw] = thumb

    output_image.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_image), sheet)


def build_closeups(video_path: Path, out_face: Path, out_mouth: Path, out_eyes: Path) -> None:
    """Extract and compile high-resolution close-ups of face, mouth, and eyes across keyframes."""
    detector_path = BACKEND_ROOT / "models_cache" / "avatar" / "face_detector" / "face_detection_yunet_2023mar.onnx"
    detector = cv2.FaceDetectorYN.create(str(detector_path), "", (320, 320), score_threshold=0.6)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    dur = total_frames / fps
    timestamps = [max(0.2, dur * frac) for frac in [0.15, 0.35, 0.55, 0.75, 0.90]]
    face_crops = []
    mouth_crops = []
    eye_crops = []

    for t in timestamps:
        frame_rgb = extract_frame_at_sec(video_path, t)
        h, w = frame_rgb.shape[:2]
        small = cv2.resize(frame_rgb, (320, 320))
        detector.setInputSize((320, 320))
        _, faces = detector.detect(small)

        if faces is not None and len(faces) > 0:
            box = faces[0][:4]
            scale_w, scale_h = 320 / w, 320 / h
            x, y, bw, bh = int(box[0] / scale_w), int(box[1] / scale_h), int(box[2] / scale_w), int(box[3] / scale_h)
            landmarks = faces[0][4:14].reshape(5, 2)
            landmarks[:, 0] /= scale_w
            landmarks[:, 1] /= scale_h

            # Face Crop
            fy1, fy2 = max(0, y - int(bh * 0.1)), min(h, y + bh + int(bh * 0.1))
            fx1, fx2 = max(0, x - int(bw * 0.1)), min(w, x + bw + int(bw * 0.1))
            f_crop = cv2.resize(frame_rgb[fy1:fy2, fx1:fx2], (256, 256))
            face_crops.append(cv2.cvtColor(f_crop, cv2.COLOR_RGB2BGR))

            # Mouth Crop
            mr, ml = landmarks[3], landmarks[4]
            mcx, mcy = int((mr[0] + ml[0]) / 2), int((mr[1] + ml[1]) / 2)
            mw, mh = int(bw * 0.35), int(bh * 0.22)
            my1, my2 = max(0, mcy - mh), min(h, mcy + mh)
            mx1, mx2 = max(0, mcx - mw), min(w, mcx + mw)
            m_crop = cv2.resize(frame_rgb[my1:my2, mx1:mx2], (256, 160))
            mouth_crops.append(cv2.cvtColor(m_crop, cv2.COLOR_RGB2BGR))

            # Eyes Crop
            er, el = landmarks[0], landmarks[1]
            ecx, ecy = int((er[0] + el[0]) / 2), int((er[1] + el[1]) / 2)
            ew, eh = int(bw * 0.45), int(bh * 0.18)
            ey1, ey2 = max(0, ecy - eh), min(h, ecy + eh)
            ex1, ex2 = max(0, ecx - ew), min(w, ecx + ew)
            e_crop = cv2.resize(frame_rgb[ey1:ey2, ex1:ex2], (256, 120))
            eye_crops.append(cv2.cvtColor(e_crop, cv2.COLOR_RGB2BGR))

    if face_crops:
        face_strip = np.hstack(face_crops)
        cv2.imwrite(str(out_face), face_strip)
    if mouth_crops:
        mouth_strip = np.hstack(mouth_crops)
        cv2.imwrite(str(out_mouth), mouth_strip)
    if eye_crops:
        eye_strip = np.hstack(eye_crops)
        cv2.imwrite(str(out_eyes), eye_strip)


def create_not_executed_panel(width: int, height: int, title: str, subtitle: str) -> np.ndarray:
    """Create a dark informational placeholder panel explicitly stating NOT EXECUTED."""
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    panel[:] = (30, 30, 38)  # Dark slate

    # Draw border
    cv2.rectangle(panel, (4, 4), (width - 4, height - 4), (70, 70, 85), 2)

    # Text lines
    cv2.putText(panel, title, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (220, 220, 230), 2)
    cv2.putText(panel, "NOT EXECUTED", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
    cv2.putText(panel, subtitle, (20, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 175), 1)
    cv2.putText(panel, "CUDA GPU REQUIRED", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 180, 255), 2)
    cv2.putText(panel, "Ready for GPU execution", (20, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 140), 1)

    return panel


def build_comparison_available(
    source_img_path: Path,
    driving_vid_path: Path,
    fallback_vid_path: Path,
    out_path: Path,
) -> None:
    """Build honest 2x3 comparison grid showing available outputs and explicitly not-executed neural models."""
    pw, ph = 384, 384

    # Row 1: Available Assets
    # 1. Source Portrait
    src_rgb = cv2.imread(str(source_img_path))
    src_panel = cv2.resize(src_rgb, (pw, ph))
    cv2.putText(src_panel, "1. SOURCE PORTRAIT", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(src_panel, "Annie (1024x1024)", (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 2. Driving Motion
    drv_rgb = cv2.cvtColor(extract_frame_at_sec(driving_vid_path, 3.0), cv2.COLOR_RGB2BGR)
    drv_panel = cv2.resize(drv_rgb, (pw, ph))
    cv2.putText(drv_panel, "2. DRIVING MOTION", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(drv_panel, "Real Motion Track (T=3.0s)", (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 3. Wav2Lip CPU Fallback
    fb_rgb = cv2.cvtColor(extract_frame_at_sec(fallback_vid_path, 3.0), cv2.COLOR_RGB2BGR)
    fb_panel = cv2.resize(fb_rgb, (pw, ph))
    cv2.putText(fb_panel, "3. WAV2LIP CPU FALLBACK", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    cv2.putText(fb_panel, "Clean Lip-Sync (No Mesh)", (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1)

    row1 = np.hstack([src_panel, drv_panel, fb_panel])

    # Row 2: Neural Models (Not Executed on CPU Host)
    p_lp = create_not_executed_panel(pw, ph, "4. LIVEPORTRAIT", "Neural Motion Synthesis")
    p_mt = create_not_executed_panel(pw, ph, "5. MUSETALK 1.5", "Latent Lip Synchronization")
    p_h2 = create_not_executed_panel(pw, ph, "6. HALLO2", "Audio Portrait Diffusion")

    row2 = np.hstack([p_lp, p_mt, p_h2])

    grid = np.vstack([row1, row2])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), grid)


async def main() -> None:
    print("==================================================================")
    print("HEYZEN — NEURAL AVATAR QUALITY EVALUATION (TRUTHFUL AUDIT)")
    print("==================================================================")

    # 1. Audit Hardware
    hw = detect_hardware()
    hw_status = get_neural_avatar_hardware_status()
    print(f"1. Hardware Detected: {hw.gpu.vendor} {hw.gpu.model}")
    print(f"2. Dedicated VRAM:    {hw.gpu.vram_total_gb:.2f} GB")
    print(f"3. CUDA Operational:  {hw.gpu.cuda_available}")

    dirs = [OUTPUT_DIR_ROOT, OUTPUT_DIR_BACKEND]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Purge misleading artifacts
    print("\n[STEP 1/6] Purging any misleading or mislabeled model artifacts...")
    remove_misleading_artifacts(dirs)

    # 3. Model States Discovery
    lp_state = discover_model_state("avatar/liveportrait")
    mt_state = discover_model_state("avatar/musetalk")
    h2_state = discover_model_state("avatar/hallo2")
    w2l_state = discover_model_state("avatar/wav2lip")

    print("\n[STEP 2/6] Querying Provider Model Readiness:")
    print(f" - LivePortrait: {lp_state['status']} ({lp_state['reason']})")
    print(f" - MuseTalk 1.5: {mt_state['status']} ({mt_state['reason']})")
    print(f" - Hallo2:       {h2_state['status']} ({h2_state['reason']})")
    print(f" - Wav2Lip:      {w2l_state['status']} ({w2l_state['reason']})")

    # 4. Source package assets
    annie_src = BACKEND_ROOT / "avatars" / "annie" / "source.png"
    if not annie_src.exists():
        annie_src = REPO_ROOT / "avatars" / "annie" / "source.png"

    annie_drv = BACKEND_ROOT / "avatars" / "annie" / "driving" / "talking.mp4"
    if not annie_drv.exists():
        annie_drv = REPO_ROOT / "avatars" / "annie" / "driving" / "talking.mp4"

    # Copy genuine source and driving files to output directories
    for d in dirs:
        shutil.copy2(str(annie_src), str(d / "source.png"))
        shutil.copy2(str(annie_drv), str(d / "driving.mp4"))

    # 5. Execute Wav2Lip fallback (Development Fallback)
    print("\n[STEP 3/6] Generating Annie Wav2Lip CPU Fallback video...")
    out_fb_root = OUTPUT_DIR_ROOT / "annie_wav2lip_fallback.mp4"
    out_fb_backend = OUTPUT_DIR_BACKEND / "annie_wav2lip_fallback.mp4"

    with tempfile.TemporaryDirectory(prefix="avatar_eval_") as tmpdir:
        tmp_path = Path(tmpdir)
        annie_wav = tmp_path / "annie_10s.wav"
        await synthesize_speech(ANNIE_SCRIPT, "en_US-lessac-medium", annie_wav)

        gpu_provider = GPUAvatarProvider(allow_fallback=True)
        t0 = time.perf_counter()
        vid_bytes, dur, frames = await gpu_provider.generate_talking_video(
            avatar_image_bytes=annie_src.read_bytes(),
            audio_bytes=annie_wav.read_bytes(),
            fps=25,
            options={"avatar_name": "annie", "enable_legacy_delaunay": False},
        )
        gen_time = time.perf_counter() - t0

        out_fb_root.write_bytes(vid_bytes)
        out_fb_backend.write_bytes(vid_bytes)

        # Validate with FFprobe
        ffprobe = FFprobeService()
        probe = await ffprobe.validate_render_output(out_fb_root)
        fb_sha = compute_sha256(out_fb_root)

        print(f" -> Output: {out_fb_root}")
        print(f" -> Duration: {probe.duration_seconds:.2f}s | Frames: {frames} | FPS: {probe.fps or 25.0}")
        print(f" -> Generation Time: {gen_time:.2f}s | SHA256: {fb_sha[:16]}...")

        # 6. Generate contact sheet and close-ups
        print("\n[STEP 4/6] Generating contact sheets and facial close-ups from genuine fallback...")
        cs_root = OUTPUT_DIR_ROOT / "fallback_contact_sheet.jpg"
        build_contact_sheet(out_fb_root, cs_root)
        shutil.copy2(str(cs_root), str(OUTPUT_DIR_BACKEND / "fallback_contact_sheet.jpg"))
        shutil.copy2(str(cs_root), str(OUTPUT_DIR_ROOT / "contact_sheet.jpg"))
        shutil.copy2(str(cs_root), str(OUTPUT_DIR_BACKEND / "contact_sheet.jpg"))

        fc_root = OUTPUT_DIR_ROOT / "face_closeups.jpg"
        mc_root = OUTPUT_DIR_ROOT / "mouth_closeups.jpg"
        ec_root = OUTPUT_DIR_ROOT / "eye_closeups.jpg"
        build_closeups(out_fb_root, fc_root, mc_root, ec_root)
        shutil.copy2(str(fc_root), str(OUTPUT_DIR_BACKEND / "face_closeups.jpg"))
        shutil.copy2(str(mc_root), str(OUTPUT_DIR_BACKEND / "mouth_closeups.jpg"))
        shutil.copy2(str(ec_root), str(OUTPUT_DIR_BACKEND / "eye_closeups.jpg"))

        # 7. Generate Honest Comparison Grid
        print("\n[STEP 5/6] Building honest comparison matrix (comparison_available.jpg)...")
        comp_root = OUTPUT_DIR_ROOT / "comparison_available.jpg"
        build_comparison_available(
            source_img_path=annie_src,
            driving_vid_path=annie_drv,
            fallback_vid_path=out_fb_root,
            out_path=comp_root,
        )
        shutil.copy2(str(comp_root), str(OUTPUT_DIR_BACKEND / "comparison_available.jpg"))

        # Generate Legacy Delaunay ablation for visual comparison
        legacy_provider = LegacyDelaunayAvatarProvider()
        leg_bytes, _, _ = await legacy_provider.generate_talking_video(
            avatar_image_bytes=annie_src.read_bytes(),
            audio_bytes=annie_wav.read_bytes(),
            fps=25,
            options={"enable_legacy_delaunay": True},
        )
        legacy_mp4 = tmp_path / "legacy_delaunay.mp4"
        legacy_mp4.write_bytes(leg_bytes)

        f_src = cv2.resize(extract_frame_at_sec(out_fb_root, 0.0), (384, 384))
        f_clean = cv2.resize(extract_frame_at_sec(out_fb_root, 3.0), (384, 384))
        f_legacy = cv2.resize(extract_frame_at_sec(legacy_mp4, 3.0), (384, 384))
        cv2.putText(f_src, "1. SOURCE PORTRAIT", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(f_clean, "2. CLEAN WAV2LIP (NO MESH)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(f_legacy, "3. LEGACY DELAUNAY (WARPED)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        ablation_img = np.hstack([f_src, f_clean, f_legacy])
        cv2.imwrite(str(OUTPUT_DIR_ROOT / "comparison_ablation.jpg"), cv2.cvtColor(ablation_img, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(OUTPUT_DIR_BACKEND / "comparison_ablation.jpg"), cv2.cvtColor(ablation_img, cv2.COLOR_RGB2BGR))

        # 8. Create Manifest and Execution Logs
        print("\n[STEP 6/6] Generating manifest.json and execution.json...")
        manifest = {
            "source": "source.png",
            "driving_motion": "driving.mp4",
            "providers": {
                "wav2lip": {
                    "status": "EXECUTED",
                    "hardware": "CPU",
                    "output": "annie_wav2lip_fallback.mp4",
                },
                "liveportrait": {
                    "status": lp_state["status"],
                    "output": None,
                },
                "musetalk": {
                    "status": mt_state["status"],
                    "output": None,
                },
                "hallo2": {
                    "status": h2_state["status"],
                    "output": None,
                },
            },
        }

        execution = {
            "liveportrait": {
                "executed": False,
                "reason": "CUDA_REQUIRED",
                "notes": "LivePortrait requires NVIDIA CUDA GPU with >=4.0GB VRAM.",
            },
            "musetalk": {
                "executed": False,
                "reason": "CUDA_REQUIRED",
                "notes": "MuseTalk 1.5 requires NVIDIA CUDA GPU with >=4.0GB VRAM.",
            },
            "hallo2": {
                "executed": False,
                "reason": "CUDA_REQUIRED",
                "notes": "Hallo2 requires NVIDIA CUDA GPU with >=8.0GB VRAM.",
            },
            "wav2lip": {
                "executed": True,
                "hardware": "CPU",
                "provider": "wav2lip",
                "model": "wav2lip-onnx",
                "model_version": "1.0.0",
                "gpu_name": f"{hw.gpu.vendor} {hw.gpu.model} (CPU Execution)",
                "duration": round(probe.duration_seconds, 2),
                "fps": float(probe.fps or 25.0),
                "frame_count": int(frames),
                "generation_time": round(gen_time, 2),
                "output_sha256": fb_sha,
                "ffprobe_validated": True,
            },
        }

        manifest_str = json.dumps(manifest, indent=2)
        execution_str = json.dumps(execution, indent=2)

        for d in dirs:
            (d / "manifest.json").write_text(manifest_str, encoding="utf-8")
            (d / "execution.json").write_text(execution_str, encoding="utf-8")

    print("\n" + "=" * 70)
    print("EVALUATION & QUALITY AUDIT COMPLETE:")
    print(f" - Manifest:           {OUTPUT_DIR_ROOT / 'manifest.json'}")
    print(f" - Execution Log:      {OUTPUT_DIR_ROOT / 'execution.json'}")
    print(f" - Fallback Video:     {OUTPUT_DIR_ROOT / 'annie_wav2lip_fallback.mp4'}")
    print(f" - Comparison Grid:    {OUTPUT_DIR_ROOT / 'comparison_available.jpg'}")
    print(f" - Ablation Matrix:    {OUTPUT_DIR_ROOT / 'comparison_ablation.jpg'}")
    print(f" - Contact Sheet:      {OUTPUT_DIR_ROOT / 'fallback_contact_sheet.jpg'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
