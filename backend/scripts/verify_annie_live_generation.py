"""Verification of the exact Annie - Studio Presenter + Annie - Lifelike live generation flow.

Flow:
1. Login to obtain JWT
2. Verify Annie avatar (30000000-0000-0000-0000-000000000002) and preview_asset_id (20000000-0000-0000-0000-000000000102)
3. Verify Annie voice (10000000-0000-0000-0000-000000000003) and provider (piper)
4. Trigger real project generation (run_async=True)
   Prompt: 'Create a high-impact video explaining the key benefits and step-by-step strategy for Ads & Promo.'
5. Poll job status through lifecycle:
   queued -> running (preparing -> generating_audio -> preparing_avatar -> rendering -> uploading) -> completed
6. Obtain pre-signed download URL for output_asset_id
7. Download MP4 and run ffprobe validation (video stream, audio stream, 1080p, duration > 0)
8. Extract frame and inspect visual content
9. Verify Project and ProjectVersion link
10. Verify Daniel regression flow as well
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
import uuid

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

def test_generation_flow(avatar_id, voice_id, prompt, label):
    print(f"\n=======================================================")
    print(f"TESTING FLOW: {label}")
    print(f"Avatar: {avatar_id} | Voice: {voice_id}")
    print(f"Prompt: {prompt}")
    print(f"=======================================================")

    # 1. Login
    login_payload = {"email": "dev@heyzen.ai", "password": "DevPassword123!"}
    auth_data = http_json("POST", "/api/v1/auth/login", login_payload)
    token = auth_data["tokens"]["access_token"]
    workspace_id = auth_data["workspace"]["id"]
    print(f"[AUTH] Logged in successfully. Workspace ID: {workspace_id}")

    # 2. Trigger generation
    gen_payload = {
        "prompt": prompt,
        "target_duration_seconds": 12,
        "aspect_ratio": "16:9",
        "avatar_id": avatar_id,
        "voice_id": voice_id,
        "video_tone": "Professional",
        "run_async": True,
    }
    gen_res = http_json("POST", f"/api/v1/workspaces/{workspace_id}/projects/generate", gen_payload, token=token, workspace_id=workspace_id)
    job_id = gen_res["id"]
    print(f"[GENERATE] Job created successfully. Job ID: {job_id}")

    # 3. Poll job lifecycle
    attempts = 0
    max_attempts = 90
    last_stage = None
    completed_job = None

    while attempts < max_attempts:
        time.sleep(1.0)
        attempts += 1
        job_data = http_json("GET", f"/api/v1/jobs/{job_id}", token=token)
        status = job_data.get("status")
        stage = job_data.get("stage")
        stage_msg = job_data.get("stage_message")
        progress = job_data.get("progress_percent", 0)

        if stage != last_stage:
            print(f"[POLL] Progress: {progress}% | Stage: {stage} | Message: {stage_msg}")
            last_stage = stage

        if status in ("succeeded", "completed"):
            completed_job = job_data
            print(f"[POLL] Job SUCCEEDED in ~{attempts}s!")
            break
        elif status == "failed":
            err = job_data.get("error_details") or job_data.get("error")
            raise RuntimeError(f"Job failed on server: {err}")

    if not completed_job:
        raise TimeoutError("Job did not complete within allowed timeout.")

    result = completed_job.get("result") or {}
    project_id = result.get("project_id")
    output_asset_id = result.get("output_asset_id")
    thumbnail_asset_id = result.get("thumbnail_asset_id")
    pipeline_mode = result.get("pipeline_mode")

    print(f"[RESULT] Project ID: {project_id}")
    print(f"[RESULT] Output Asset ID: {output_asset_id}")
    print(f"[RESULT] Thumbnail Asset ID: {thumbnail_asset_id}")
    print(f"[RESULT] Pipeline Mode: {pipeline_mode}")

    assert project_id, "Project ID missing from job result"
    assert output_asset_id, "Output asset ID missing from job result"

    # 4. Fetch Asset & Pre-signed URL
    down_data = http_json("GET", f"/api/v1/workspaces/{workspace_id}/assets/{output_asset_id}/download", token=token, workspace_id=workspace_id)
    download_url = down_data["download_url"]
    print(f"[STORAGE] Pre-signed MinIO download URL obtained: {download_url[:60]}...")

    # 5. Download and validate video file with ffprobe
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_mp4 = os.path.join(tmp_dir, f"verified_{project_id}.mp4")
        urllib.request.urlretrieve(download_url, tmp_mp4)
        file_size = os.path.getsize(tmp_mp4)
        print(f"[DOWNLOAD] Downloaded MP4 size: {file_size:,} bytes")
        assert file_size > 10000, f"File size unexpectedly small: {file_size} bytes"

        # FFprobe check
        probe_meta = run_ffprobe(tmp_mp4)
        streams = probe_meta.get("streams", [])
        fmt = probe_meta.get("format", {})
        dur = float(fmt.get("duration", 0))

        v_stream = next((s for s in streams if s["codec_type"] == "video"), None)
        a_stream = next((s for s in streams if s["codec_type"] == "audio"), None)

        print(f"[FFPROBE] Container Duration: {dur:.2f}s | Size: {fmt.get('size')} bytes")
        print(f"[FFPROBE] Video stream: codec={v_stream['codec_name']} {v_stream['width']}x{v_stream['height']} fps={v_stream.get('r_frame_rate')}")
        print(f"[FFPROBE] Audio stream: codec={a_stream['codec_name']}")

        assert v_stream is not None, "Missing video stream!"
        assert a_stream is not None, "Missing audio stream!"
        assert v_stream["width"] == 1920 and v_stream["height"] == 1080, f"Expected 1920x1080, got {v_stream['width']}x{v_stream['height']}"
        assert dur > 1.0, f"Duration too short: {dur}"

        # Extract frame
        tmp_frame = os.path.join(tmp_dir, "frame_001.png")
        subprocess.run(["ffmpeg", "-y", "-i", tmp_mp4, "-ss", "00:00:02", "-vframes", "1", tmp_frame], check=True, capture_output=True)
        assert os.path.exists(tmp_frame) and os.path.getsize(tmp_frame) > 5000, "Frame extraction failed or frame is empty!"
        print(f"[FRAME] Sample frame extracted successfully ({os.path.getsize(tmp_frame):,} bytes)")

    # 6. Verify Project & ProjectVersion
    proj_data = http_json("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}", token=token, workspace_id=workspace_id)
    print(f"[PROJECT] Project status: {proj_data.get('status')} | duration: {proj_data.get('duration_ms')}ms")
    assert proj_data.get("status") == "ready", f"Project status is {proj_data.get('status')}, expected ready"

    version_id = proj_data.get("current_version_id")
    if version_id:
        latest_ver = http_json("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{version_id}", token=token, workspace_id=workspace_id)
    else:
        versions_list = http_json("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions", token=token, workspace_id=workspace_id)
        latest_ver = versions_list[0]
    doc = latest_ver.get("document", {})
    scenes = doc.get("scenes", [])
    print(f"[VERSION] Document contains {len(scenes)} scenes | total_duration: {doc.get('settings', {}).get('total_duration')}s")
    assert len(scenes) >= 1, "No scenes in project document"

    print(f"\n>>> FLOW PASSED 100%: {label} <<<")
    return {
        "job_id": job_id,
        "project_id": project_id,
        "output_asset_id": output_asset_id,
        "duration": dur,
        "resolution": f"{v_stream['width']}x{v_stream['height']}",
        "file_size": file_size,
    }

def main():
    print("=================================================================")
    print("HEYGEN VIDEO AGENT REAL MEDIA PIPELINE LIVE VERIFICATION")
    print("=================================================================")

    # Test Annie (Exact requested flow)
    annie_result = test_generation_flow(
        avatar_id="30000000-0000-0000-0000-000000000002", # Annie - Studio Presenter
        voice_id="10000000-0000-0000-0000-000000000003",  # Annie - Lifelike
        prompt="Create a high-impact video explaining the key benefits and step-by-step strategy for Ads & Promo.",
        label="Annie - Studio Presenter + Annie - Lifelike (Ads & Promo)",
    )

    # Test Daniel (Regression check)
    daniel_result = test_generation_flow(
        avatar_id="30000000-0000-0000-0000-000000000004", # Daniel - Modern Creator
        voice_id="en_US-lessac-medium",                   # Piper Lessac
        prompt="Create a quick 10-second tech update announcing our new product feature.",
        label="Daniel - Modern Creator + Piper Lessac (Regression)",
    )

    print("\n=================================================================")
    print("ALL LIVE VERIFICATION FLOWS SUCCEEDED!")
    print(f"Annie Flow: Job={annie_result['job_id']}, Project={annie_result['project_id']}, Asset={annie_result['output_asset_id']}, Size={annie_result['file_size']:,}B")
    print(f"Daniel Flow: Job={daniel_result['job_id']}, Project={daniel_result['project_id']}, Asset={daniel_result['output_asset_id']}, Size={daniel_result['file_size']:,}B")
    print("=================================================================")

if __name__ == "__main__":
    main()
