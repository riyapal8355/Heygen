import asyncio
import copy
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import cv2
import numpy as np
from PIL import Image as PILImage

sys.path.insert(0, os.path.abspath("."))

from app.ai.adapters.wav2lip import Wav2LipONNXAvatarProvider
from app.ai.adapters.piper import PiperTTSProvider

BASE_URL = "http://127.0.0.1:8000"

def http_json(method, path, data=None, token=None, workspace_id=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if workspace_id:
        headers["X-Workspace-Id"] = str(workspace_id)
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def extract_frame_at(video_path, time_sec, out_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{time_sec:.3f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

def run_ffprobe(video_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def generate_standalone_avatar(avatar_path, voice_model, prefix, out_dir):
    print(f"\n[STANDALONE] Generating standalone avatar for {prefix} ({avatar_path.name})...")
    tts = PiperTTSProvider()
    script = (
        "Welcome to HeyZen. We provide professional studio avatars that speak naturally "
        "with authentic facial expressions, organic head motion, and synchronized speech. "
        "Create studio quality marketing videos in seconds."
    )
    tts_res = tts._synthesize_sync(text=script, voice_id=voice_model)
    wav2lip = Wav2LipONNXAvatarProvider()
    mp4_bytes, out_dur, frame_count = asyncio.run(
        wav2lip.synthesize_avatar_video(
            avatar_image_bytes=avatar_path.read_bytes(),
            audio_bytes=tts_res.audio_bytes,
            fps=25,
        )
    )
    mp4_path = out_dir / f"{prefix}_avatar_only.mp4" if prefix != "annie" else out_dir / "avatar_only.mp4"
    mp4_path.write_bytes(mp4_bytes)
    print(f"[STANDALONE] Saved {mp4_path.name} ({out_dur:.2f}s, {frame_count} frames)")

    # Build 10-second contact sheet
    cap = cv2.VideoCapture(str(mp4_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for sec in range(0, 11):
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(tot - 1, int(sec * fps)))
        ret, fr = cap.read()
        if ret and fr is not None:
            fr_rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            p_img = PILImage.fromarray(fr_rgb).resize((320, 180), PILImage.Resampling.LANCZOS)
            frames.append(p_img)
    cap.release()

    cols = 4
    rows = int(np.ceil(len(frames) / cols))
    sheet = PILImage.new("RGB", (cols * 320, rows * 180), (10, 14, 26))
    for i, fr in enumerate(frames):
        sheet.paste(fr, ((i % cols) * 320, (i // cols) * 180))
    sheet_name = f"{prefix}_avatar_contact_sheet.jpg" if prefix != "annie" else "avatar_contact_sheet.jpg"
    sheet.save(out_dir / sheet_name, quality=95)
    print(f"[STANDALONE] Saved {sheet_name}")

def generate_project_video(token, workspace_id, avatar_id, voice_id, prompt, prefix, out_dir):
    print(f"\n[PROJECT] Triggering full project generation for {prefix}...")
    gen_payload = {
        "prompt": prompt,
        "target_duration_seconds": 13,
        "aspect_ratio": "16:9",
        "avatar_id": avatar_id,
        "voice_id": voice_id,
        "video_tone": "Professional",
        "run_async": True,
    }
    res = http_json(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/projects/generate",
        gen_payload,
        token=token,
        workspace_id=workspace_id,
    )
    job_id = res["id"]
    print(f"[JOB] Job ID: {job_id}")

    start_t = time.time()
    completed_job = None
    seen = set()
    while time.time() - start_t < 240:
        p = http_json("GET", f"/api/v1/jobs/{job_id}", token=token)
        st = p.get("status")
        stage = p.get("stage")
        pct = p.get("progress_percent", 0)
        k = f"{stage}:{pct}"
        if k not in seen:
            seen.add(k)
            print(f"  -> [{st.upper()}] {stage} ({pct}%) - {p.get('stage_message')}")
        if st in ("succeeded", "completed"):
            completed_job = p
            break
        elif st == "failed":
            raise RuntimeError(f"Job failed: {p.get('error_details')}")
        time.sleep(1.5)

    assert completed_job is not None, f"Job {job_id} timed out"
    out_asset_id = completed_job["result"]["output_asset_id"]

    down_info = http_json(
        "GET",
        f"/api/v1/workspaces/{workspace_id}/assets/{out_asset_id}/download",
        token=token,
        workspace_id=workspace_id,
    )
    v_name = f"{prefix}_final.mp4" if prefix != "annie" else "final.mp4"
    final_video = out_dir / v_name
    urllib.request.urlretrieve(down_info["download_url"], str(final_video))
    print(f"[PROJECT] Saved {v_name} ({final_video.stat().st_size / (1024*1024):.2f} MB)")

    probe = run_ffprobe(str(final_video))
    dur = float(probe["format"]["duration"])
    v_st = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a_st = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    print(f"[PROBE] {v_st['width']}x{v_st['height']} {v_st['codec_name']}, {a_st['codec_name']}, dur={dur:.2f}s")

    # 1. Scene Contact Sheet
    t1 = min(2.0, dur * 0.15)
    t2 = dur * 0.50
    t3 = min(dur - 0.8, dur * 0.85)

    f1 = out_dir / f"{prefix}_sc1.jpg"
    f2 = out_dir / f"{prefix}_sc2.jpg"
    f3 = out_dir / f"{prefix}_sc3.jpg"
    extract_frame_at(final_video, t1, f1)
    extract_frame_at(final_video, t2, f2)
    extract_frame_at(final_video, t3, f3)

    img1 = PILImage.open(f1).resize((960, 540), PILImage.Resampling.LANCZOS)
    img2 = PILImage.open(f2).resize((960, 540), PILImage.Resampling.LANCZOS)
    img3 = PILImage.open(f3).resize((960, 540), PILImage.Resampling.LANCZOS)

    sheet_sc = PILImage.new("RGB", (1920, 1080), (10, 14, 26))
    sheet_sc.paste(img1, (0, 0))
    sheet_sc.paste(img2, (960, 0))
    sheet_sc.paste(img3, (480, 540))
    sc_name = f"{prefix}_scene_contact_sheet.jpg" if prefix != "annie" else "scene_contact_sheet.jpg"
    sheet_sc.save(out_dir / sc_name, quality=95)
    print(f"[CONTACT SHEET] Saved {sc_name}")

    # 2. Final Timeline Contact Sheet
    sample_times = [round(i * (dur / 10.0), 2) for i in range(10)]
    sample_times.append(round(dur - 0.5, 2))
    tw, th = 480, 270
    cols = 3
    rows = int(np.ceil(len(sample_times) / cols))
    sheet_fin = PILImage.new("RGB", (cols * tw, rows * th), (10, 14, 26))

    for idx, ts in enumerate(sample_times):
        tmp_fr = out_dir / f"{prefix}_tmp_{idx:02d}.jpg"
        extract_frame_at(final_video, ts, tmp_fr)
        p_th = PILImage.open(tmp_fr).resize((tw, th), PILImage.Resampling.LANCZOS)
        sheet_fin.paste(p_th, ((idx % cols) * tw, (idx // cols) * th))
        if tmp_fr.exists():
            tmp_fr.unlink()

    fin_name = f"{prefix}_final_contact_sheet.jpg" if prefix != "annie" else "final_contact_sheet.jpg"
    sheet_fin.save(out_dir / fin_name, quality=95)
    print(f"[CONTACT SHEET] Saved {fin_name}")

    # 3. Transition Contact Sheet
    trans_times = [3.8, 4.0, 4.2, dur * 0.70 - 0.2, dur * 0.70, dur * 0.70 + 0.2]
    trans_times = [min(ts, dur - 0.2) for ts in trans_times]
    sheet_tr = PILImage.new("RGB", (3 * tw, 2 * th), (10, 14, 26))
    for idx, ts in enumerate(trans_times):
        tmp_fr = out_dir / f"{prefix}_tr_{idx:02d}.jpg"
        extract_frame_at(final_video, ts, tmp_fr)
        p_th = PILImage.open(tmp_fr).resize((tw, th), PILImage.Resampling.LANCZOS)
        sheet_tr.paste(p_th, ((idx % 3) * tw, (idx // 3) * th))
        if tmp_fr.exists():
            tmp_fr.unlink()

    tr_name = f"{prefix}_transition_contact_sheet.jpg" if prefix != "annie" else "transition_contact_sheet.jpg"
    sheet_tr.save(out_dir / tr_name, quality=95)
    print(f"[CONTACT SHEET] Saved {tr_name}")

def main():
    print("=" * 70)
    print("EXECUTING COMPREHENSIVE VALIDATION SUITE (ANNIE & DANIEL)")
    print("=" * 70)

    out_dirs = [
        Path("test-results/visual_quality").resolve(),
        (Path("..") / "test-results" / "visual_quality").resolve(),
    ]
    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)
    primary = out_dirs[0]

    # Auth
    auth = http_json("POST", "/api/v1/auth/login", {"email": "dev@heyzen.ai", "password": "DevPassword123!"})
    token = auth["tokens"]["access_token"]
    ws_id = auth["workspace"]["id"]
    print(f"[AUTH] Logged in. Workspace ID: {ws_id}")

    # --- 1. ANNIE RE-RENDER WITH CLEAN CUT TRANSITIONS ---
    print("\n--- STAGE A: ANNIE VERIFICATION (BROADCAST CUT TRANSITIONS) ---")
    annie_prompt = "Create high-impact marketing videos with realistic AI avatars and natural speech."
    generate_project_video(
        token=token,
        workspace_id=ws_id,
        avatar_id="30000000-0000-0000-0000-000000000002",
        voice_id="10000000-0000-0000-0000-000000000003",
        prompt=annie_prompt,
        prefix="annie",
        out_dir=primary,
    )

    # --- 2. DANIEL VERIFICATION (STANDALONE + FULL PROJECT) ---
    print("\n--- STAGE B: DANIEL VERIFICATION (STANDALONE + FULL PROJECT) ---")
    daniel_avatar_path = Path("seed_assets/avatars/daniel_modern_creator.jpg")
    generate_standalone_avatar(
        avatar_path=daniel_avatar_path,
        voice_model="en_US-bryce-medium",
        prefix="daniel",
        out_dir=primary,
    )

    daniel_prompt = "Build engaging product demos with modern AI avatars and seamless voice narration."
    generate_project_video(
        token=token,
        workspace_id=ws_id,
        avatar_id="30000000-0000-0000-0000-000000000004",
        voice_id="10000000-0000-0000-0000-000000000004",
        prompt=daniel_prompt,
        prefix="daniel",
        out_dir=primary,
    )

    # Mirror all generated artifacts to the root directory
    for item in primary.glob("*.*"):
        shutil.copy2(item, out_dirs[1] / item.name)

    print("\n[COMPLETE] Comprehensive validation suite finished successfully for Annie and Daniel!")

if __name__ == "__main__":
    main()
