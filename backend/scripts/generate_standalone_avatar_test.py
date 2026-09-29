import os
import sys
import time
import math
import cv2
import numpy as np
from pathlib import Path
from PIL import Image as PILImage

sys.path.insert(0, os.path.abspath("."))

from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.adapters.piper import PiperTTSProvider
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService

def main():
    print("=" * 65)
    print("STAGE 1: GENERATING STANDALONE TALKING AVATAR VIDEO (ANNIE)")
    print("=" * 65)

    output_dir = Path("test-results/visual_quality")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize real 10-second speech audio using Piper TTS
    tts = PiperTTSProvider()
    script_text = (
        "Welcome to HeyZen. We provide professional studio avatars that speak naturally "
        "with authentic facial expressions, organic head motion, and synchronized speech. "
        "Create studio quality marketing videos in seconds."
    )
    print(f"[TTS] Synthesizing speech: '{script_text[:40]}...'")
    tts_result = tts._synthesize_sync(
        text=script_text,
        voice_id="en_US-lessac-medium",
    )
    audio_bytes = tts_result.audio_bytes
    duration = tts_result.duration_seconds
    print(f"[TTS] Speech synthesized: {duration:.2f} seconds ({len(audio_bytes)} bytes)")

    # 2. Load high-res avatar source
    avatar_path = Path("seed_assets/avatars/annie_studio_presenter.jpg")
    assert avatar_path.exists(), f"Avatar not found at {avatar_path}"
    avatar_bytes = avatar_path.read_bytes()
    img_bgr = cv2.imread(str(avatar_path))
    print(f"[AVATAR] Loaded source avatar: {img_bgr.shape[1]}x{img_bgr.shape[0]}")

    # 3. Synthesize talking avatar video
    wav2lip = Wav2LipONNXAvatarProvider()
    print("[WAV2LIP] Generating talking avatar video with 3D head motion...")
    import asyncio
    t0 = time.time()
    mp4_bytes, out_dur, frame_count = asyncio.run(
        wav2lip.synthesize_avatar_video(
            avatar_image_bytes=avatar_bytes,
            audio_bytes=audio_bytes,
            fps=25,
        )
    )
    elapsed = time.time() - t0
    print(f"[WAV2LIP] Generated {frame_count} frames ({out_dur:.2f}s) in {elapsed:.1f}s")

    # 4. Save avatar_only.mp4
    avatar_mp4_path = output_dir / "avatar_only.mp4"
    avatar_mp4_path.write_bytes(mp4_bytes)
    print(f"[SAVED] Standalone avatar video saved to {avatar_mp4_path}")

    # 5. Extract representative frames at 0s, 1s, 2s, 3s, 4s, 5s, 6s, 7s, 8s, 9s, 10s
    cap = cv2.VideoCapture(str(avatar_mp4_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[FRAMES] Extracting representative frames (FPS: {fps}, Total: {total_frames})...")

    req_seconds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    extracted_frames = {}

    for sec in req_seconds:
        f_idx = min(total_frames - 1, int(sec * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            extracted_frames[sec] = frame
            frame_file = output_dir / f"avatar_frame_{sec:02d}s.jpg"
            cv2.imwrite(str(frame_file), frame)
            print(f"  - Extracted {sec}s (frame {f_idx}) -> {frame_file.name}")
    cap.release()

    # 6. Extract face, eye, and mouth crops from 2s, 5s, 8s
    detector = cv2.FaceDetectorYN.create(
        str(Path("models_cache/avatar/face_detector/face_detection_yunet_2023mar.onnx")),
        "", (320, 320), 0.5, 0.3
    )

    for sec in [2, 5, 8]:
        if sec in extracted_frames:
            fr = extracted_frames[sec]
            h, w = fr.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(fr)
            if faces is not None and len(faces) > 0:
                box = faces[0][:4].astype(int)
                bx, by, bw, bh = box
                face_crop = fr[max(0, by):min(h, by+bh), max(0, bx):min(w, bx+bw)]
                cv2.imwrite(str(output_dir / f"face_crop_{sec}s.jpg"), face_crop)

                # Eye crop
                re_x, re_y = int(faces[0][4]), int(faces[0][5])
                le_x, le_y = int(faces[0][6]), int(faces[0][7])
                eye_y1 = max(0, min(re_y, le_y) - 20)
                eye_y2 = min(h, max(re_y, le_y) + 20)
                eye_x1 = max(0, min(re_x, le_x) - 30)
                eye_x2 = min(w, max(re_x, le_x) + 30)
                cv2.imwrite(str(output_dir / f"eye_crop_{sec}s.jpg"), fr[eye_y1:eye_y2, eye_x1:eye_x2])

                # Mouth crop
                rm_x, rm_y = int(faces[0][10]), int(faces[0][11])
                lm_x, lm_y = int(faces[0][12]), int(faces[0][13])
                m_cx = (rm_x + lm_x) // 2
                m_cy = (rm_y + lm_y) // 2
                m_rad = int(np.hypot(rm_x - lm_x, rm_y - lm_y) * 0.75)
                m_y1, m_y2 = max(0, m_cy - m_rad), min(h, m_cy + m_rad)
                m_x1, m_x2 = max(0, m_cx - m_rad), min(w, m_cx + m_rad)
                cv2.imwrite(str(output_dir / f"mouth_crop_{sec}s.jpg"), fr[m_y1:m_y2, m_x1:m_x2])

    # 7. Create high-resolution contact sheet (4 columns, 3 rows)
    thumb_w, thumb_h = 320, 320
    cols = 4
    rows = 3
    sheet = PILImage.new("RGB", (cols * thumb_w, rows * thumb_h), (15, 23, 42))

    for idx, sec in enumerate(req_seconds):
        if sec in extracted_frames:
            r = idx // cols
            c = idx % cols
            rgb_thumb = cv2.cvtColor(cv2.resize(extracted_frames[sec], (thumb_w, thumb_h)), cv2.COLOR_BGR2RGB)
            pil_thumb = PILImage.fromarray(rgb_thumb)
            sheet.paste(pil_thumb, (c * thumb_w, r * thumb_h))

    sheet_path = output_dir / "avatar_contact_sheet.jpg"
    sheet.save(str(sheet_path), quality=92)
    print(f"[CONTACT SHEET] Saved contact sheet to {sheet_path}")

    print("\n" + "=" * 65)
    print("STANDALONE AVATAR VERIFICATION COMPLETE")
    print("=" * 65)

if __name__ == "__main__":
    main()
