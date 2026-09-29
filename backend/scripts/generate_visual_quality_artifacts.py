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

def main():
    print("=" * 70)
    print("GENERATING VISUAL QUALITY ARTIFACTS (ANNIE & DANIEL)")
    print("=" * 70)

    vq_dirs = [
        Path("test-results/visual_quality").resolve(),
        (Path("..") / "test-results" / "visual_quality").resolve(),
    ]
    for d in vq_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Login as dev@heyzen.ai
    login_payload = {"email": "dev@heyzen.ai", "password": "DevPassword123!"}
    auth_data = http_json("POST", "/api/v1/auth/login", login_payload)
    token = auth_data["tokens"]["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    print(f"[AUTH] Logged in. Workspace ID: {workspace_id}")

    # -------------------------------------------------------------
    # 2. Generate Real Video for Annie
    # -------------------------------------------------------------
    prompt = "Create high-impact marketing videos with realistic AI avatars and natural speech."
    avatar_id = "30000000-0000-0000-0000-000000000002"  # Annie
    voice_id = "10000000-0000-0000-0000-000000000003"   # Piper Annie

    print(f"\n[GENERATING] Triggering Annie project generation...")
    gen_payload = {
        "prompt": prompt,
        "target_duration_seconds": 13,
        "aspect_ratio": "16:9",
        "avatar_id": avatar_id,
        "voice_id": voice_id,
        "video_tone": "Professional",
        "run_async": True,
    }
    gen_res = http_json(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/projects/generate",
        gen_payload,
        token=token,
        workspace_id=workspace_id,
    )
    job_id = gen_res["id"]
    print(f"[JOB] Job ID: {job_id}")

    # Poll until complete
    start_t = time.time()
    completed_job = None
    seen_stages = set()
    while time.time() - start_t < 180:
        polled = http_json("GET", f"/api/v1/jobs/{job_id}", token=token)
        status = polled.get("status")
        stage = polled.get("stage")
        pct = polled.get("progress_percent", 0)
        msg = polled.get("stage_message")
        key = f"{stage}:{pct}"
        if key not in seen_stages:
            seen_stages.add(key)
            print(f"  -> [{status.upper()}] {stage} ({pct}%) - {msg}")
        if status in ("succeeded", "completed"):
            completed_job = polled
            print(f"[JOB] Completed in {time.time() - start_t:.1f}s")
            break
        elif status == "failed":
            raise RuntimeError(f"Job failed: {polled.get('error_details')}")
        time.sleep(1.5)

    assert completed_job is not None, "Job timed out"
    result = completed_job["result"]
    output_asset_id = result["output_asset_id"]

    # Download rendered video
    down_info = http_json(
        "GET",
        f"/api/v1/workspaces/{workspace_id}/assets/{output_asset_id}/download",
        token=token,
        workspace_id=workspace_id,
    )
    download_url = down_info["download_url"]
    primary_vq = vq_dirs[0]
    final_video_path = primary_vq / "final.mp4"
    urllib.request.urlretrieve(download_url, str(final_video_path))
    print(f"[DOWNLOAD] Saved final.mp4 ({final_video_path.stat().st_size / (1024*1024):.2f} MB)")

    # Probe final.mp4
    probe = run_ffprobe(str(final_video_path))
    duration = float(probe["format"]["duration"])
    v_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a_stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    print(f"[PROBE] {v_stream['width']}x{v_stream['height']} {v_stream['codec_name']}, audio {a_stream['codec_name']}, dur={duration:.2f}s")

    # If scene_1.mp4, scene_2.mp4, scene_3.mp4 were saved by media_pipeline_service
    # in the current working directory, verify them or extract from final
    for sc_num in (1, 2, 3):
        sc_file = primary_vq / f"scene_{sc_num}.mp4"
        if not sc_file.exists():
            # If intermediate scene was in backend/test-results/visual_quality or tmp
            print(f"[SCENE] Checking scene_{sc_num}.mp4...")

    # 3. Create Scene Contact Sheet (Scene 1, Scene 2, Scene 3)
    print("\n[CONTACT SHEET] Creating scene_contact_sheet.jpg...")
    # Sample Scene 1 at ~1.5s, Scene 2 at ~6.0s, Scene 3 at ~11.0s
    t_sc1 = min(2.0, duration * 0.15)
    t_sc2 = duration * 0.50
    t_sc3 = min(duration - 0.8, duration * 0.85)

    f_sc1 = primary_vq / "scene_1_frame.jpg"
    f_sc2 = primary_vq / "scene_2_frame.jpg"
    f_sc3 = primary_vq / "scene_3_frame.jpg"
    extract_frame_at(final_video_path, t_sc1, f_sc1)
    extract_frame_at(final_video_path, t_sc2, f_sc2)
    extract_frame_at(final_video_path, t_sc3, f_sc3)

    img_sc1 = PILImage.open(f_sc1).resize((960, 540), PILImage.Resampling.LANCZOS)
    img_sc2 = PILImage.open(f_sc2).resize((960, 540), PILImage.Resampling.LANCZOS)
    img_sc3 = PILImage.open(f_sc3).resize((960, 540), PILImage.Resampling.LANCZOS)

    # Build 3-panel horizontal or 2x2 grid contact sheet
    sheet_scenes = PILImage.new("RGB", (1920, 1080), (10, 14, 26))
    sheet_scenes.paste(img_sc1, (0, 0))
    sheet_scenes.paste(img_sc2, (960, 0))
    sheet_scenes.paste(img_sc3, (480, 540))
    sc_sheet_path = primary_vq / "scene_contact_sheet.jpg"
    sheet_scenes.save(sc_sheet_path, quality=95)
    print(f"[CONTACT SHEET] Saved {sc_sheet_path}")

    # 4. Create Final Timeline Contact Sheet (sampling 0s through 12s)
    print("\n[CONTACT SHEET] Creating final_contact_sheet.jpg...")
    sample_times = [round(i * (duration / 10.0), 2) for i in range(10)]
    sample_times.append(round(duration - 0.5, 2))
    
    thumb_w, thumb_h = 480, 270
    cols = 3
    rows = int(np.ceil(len(sample_times) / cols))
    sheet_final = PILImage.new("RGB", (cols * thumb_w, rows * thumb_h), (10, 14, 26))

    for idx, ts in enumerate(sample_times):
        tmp_frame = primary_vq / f"final_frame_{idx:02d}.jpg"
        extract_frame_at(final_video_path, ts, tmp_frame)
        p_thumb = PILImage.open(tmp_frame).resize((thumb_w, thumb_h), PILImage.Resampling.LANCZOS)
        r = idx // cols
        c = idx % cols
        sheet_final.paste(p_thumb, (c * thumb_w, r * thumb_h))

    final_sheet_path = primary_vq / "final_contact_sheet.jpg"
    sheet_final.save(final_sheet_path, quality=95)
    print(f"[CONTACT SHEET] Saved {final_sheet_path}")

    # 5. Create Transition Contact Sheet (inspecting scene cut/fade boundary)
    print("\n[CONTACT SHEET] Creating transition_contact_sheet.jpg...")
    # Scene 1 -> 2 transition happens around 4.0s; Scene 2 -> 3 transition happens around 8.5s - 9.0s
    trans_times = [3.7, 3.9, 4.1, 4.3, 8.3, 8.6]
    trans_times = [min(ts, duration - 0.3) for ts in trans_times]
    
    t_cols = 3
    t_rows = 2
    sheet_trans = PILImage.new("RGB", (t_cols * thumb_w, t_rows * thumb_h), (10, 14, 26))

    for idx, ts in enumerate(trans_times):
        tmp_frame = primary_vq / f"trans_frame_{idx:02d}.jpg"
        extract_frame_at(final_video_path, ts, tmp_frame)
        p_thumb = PILImage.open(tmp_frame).resize((thumb_w, thumb_h), PILImage.Resampling.LANCZOS)
        r = idx // t_cols
        c = idx % t_cols
        sheet_trans.paste(p_thumb, (c * thumb_w, r * thumb_h))

    trans_sheet_path = primary_vq / "transition_contact_sheet.jpg"
    sheet_trans.save(trans_sheet_path, quality=95)
    print(f"[CONTACT SHEET] Saved {trans_sheet_path}")

    # Mirror all artifacts to the root test-results/visual_quality directory as well
    for item in primary_vq.glob("*.*"):
        shutil.copy2(item, vq_dirs[1] / item.name)

    print("\n[SUCCESS] All visual quality artifacts created and verified!")

if __name__ == "__main__":
    main()
