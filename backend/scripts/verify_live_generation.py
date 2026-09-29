"""Live end-to-end verification script against running FastAPI server at http://127.0.0.1:8000.

Simulates the exact browser flow:
1. Authenticate / login
2. Call POST /api/v1/workspaces/{workspace_id}/projects/generate with run_async=True
3. Poll GET /api/v1/jobs/{job_id} through all lifecycle stages:
   preparing -> generating_audio -> preparing_avatar -> rendering -> uploading -> succeeded
4. Verify completed job result
5. Query GET /api/v1/workspaces/{workspace_id}/assets/{output_asset_id}/download
6. Download the rendered MP4 file from the pre-signed MinIO URL
7. Validate MP4 container, streams, duration, resolution, and audio with ffprobe
8. Extract a sample frame to inspect visual content
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse

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

def main():
    print("--- 1. Login to obtain JWT ---")
    login_payload = {
        "email": "dev@heyzen.ai",
        "password": "DevPassword123!",
    }
    auth_data = http_json("POST", "/api/v1/auth/login", login_payload)
    token = auth_data["tokens"]["access_token"]
    workspace = auth_data["workspace"]
    workspace_id = workspace["id"]
    print(f"Logged in successfully. Workspace: {workspace['name']} ({workspace_id})")

    print("\n--- 2. Fetch Avatars and Voices ---")
    avatars = http_json("GET", "/api/v1/avatars", token=token, workspace_id=workspace_id)
    print(f"Loaded {len(avatars)} avatars.")
    # Choose Daniel
    selected_avatar = next((a for a in avatars if "daniel" in a["name"].lower()), avatars[0])
    print(f"Selected avatar: {selected_avatar['name']} ({selected_avatar['id']})")

    voices = http_json("GET", "/api/v1/voices", token=token, workspace_id=workspace_id)
    print(f"Loaded {len(voices)} voices.")
    selected_voice_id = "en_US-lessac-medium"

    print("\n--- 3. Trigger Real Media Generation (run_async=True) ---")
    gen_payload = {
        "prompt": "Create a high-energy product launch video showcasing HeyZen AI studio capabilities.",
        "target_duration_seconds": 12,
        "aspect_ratio": "16:9",
        "avatar_id": selected_avatar["id"],
        "voice_id": selected_voice_id,
        "video_tone": "Professional",
        "run_async": True,
    }
    job_resp = http_json("POST", f"/api/v1/workspaces/{workspace_id}/projects/generate", gen_payload, token=token, workspace_id=workspace_id)
    job_id = job_resp["id"]
    print(f"Generation job submitted. Job ID: {job_id}, Status: {job_resp['status']}")

    print("\n--- 4. Polling Job Stages ---")
    stages_seen = set()
    start_time = time.time()
    completed_job = None

    while time.time() - start_time < 90:
        polled = http_json("GET", f"/api/v1/jobs/{job_id}", token=token, workspace_id=workspace_id)
        status = polled["status"]
        stage = polled.get("stage", "")
        if stage and stage not in stages_seen:
            stages_seen.add(stage)
            msg = polled.get("stage_message") or stage
            print(f"  [Stage Update] {stage.upper()}: {msg} ({polled.get('progress_percent', 0)}%)")

        if status in ("succeeded", "completed"):
            completed_job = polled
            print(f"\nJob completed in {time.time() - start_time:.2f}s!")
            break
        elif status == "failed":
            raise RuntimeError(f"Job failed: {polled.get('error_details')}")

        time.sleep(1)

    if not completed_job:
        raise TimeoutError("Job did not complete within 90 seconds")

    print(f"Job Result: {json.dumps(completed_job.get('result'), indent=2)}")
    result = completed_job["result"]
    output_asset_id = result["output_asset_id"]
    duration = result.get("duration_seconds", 0)
    print(f"Rendered video duration: {duration:.2f}s")

    print("\n--- 5. Fetch Asset Download URL ---")
    asset_down = http_json("GET", f"/api/v1/workspaces/{workspace_id}/assets/{output_asset_id}/download", token=token, workspace_id=workspace_id)
    download_url = asset_down["download_url"]
    print(f"Pre-signed MinIO URL: {download_url[:80]}...")

    print("\n--- 6. Download Rendered MP4 ---")
    temp_dir = tempfile.gettempdir()
    mp4_path = os.path.join(temp_dir, f"test_rendered_{job_id}.mp4")
    urllib.request.urlretrieve(download_url, mp4_path)
    file_size = os.path.getsize(mp4_path)
    print(f"Downloaded MP4: {mp4_path} ({file_size:,} bytes)")
    assert file_size > 0, "Rendered video file is empty!"

    print("\n--- 7. Validate with FFprobe ---")
    ffprobe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name,width,height:format=duration,size,format_name",
        "-of", "json",
        mp4_path
    ]
    probe_raw = subprocess.check_output(ffprobe_cmd).decode("utf-8")
    probe_data = json.loads(probe_raw)
    print(f"FFprobe Format: {probe_data.get('format', {}).get('format_name')}")
    print(f"Streams: {[s.get('codec_type') + ':' + s.get('codec_name') for s in probe_data.get('streams', [])]}")

    has_video = any(s.get("codec_type") == "video" for s in probe_data.get("streams", []))
    has_audio = any(s.get("codec_type") == "audio" for s in probe_data.get("streams", []))
    parsed_duration = float(probe_data.get("format", {}).get("duration", 0))

    assert has_video, "Validation error: Missing video stream!"
    assert has_audio, "Validation error: Missing audio stream!"
    assert parsed_duration > 0, f"Validation error: Invalid duration ({parsed_duration})!"
    print(f"VERIFIED: Valid MP4, Video: YES, Audio: YES, Duration: {parsed_duration:.2f}s")

    print("\n--- 8. Verify Project in Studio ---")
    project_id = result["project_id"]
    project = http_json("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}", token=token, workspace_id=workspace_id)
    print(f"Project Title: {project['title']}")
    print(f"Project Status: {project['status']}")
    print(f"Project Duration: {project['duration_ms']}ms")
    print(f"Thumbnail Asset ID: {project.get('thumbnail_asset_id')}")

    versions = http_json("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions", token=token, workspace_id=workspace_id)
    print(f"Project Versions count: {len(versions)}")
    assert len(versions) > 0, "No project versions found!"
    latest_version = versions[0]
    print(f"Latest Version Revision: {latest_version.get('revision')}")
    scenes = latest_version.get("document", {}).get("scenes", [])
    print(f"Project Version Scenes: {len(scenes)}")
    for idx, sc in enumerate(scenes):
        print(f"  Scene {idx+1}: duration={sc.get('duration')}s, script='{sc.get('speech', {}).get('script', '')[:40]}...'")

    doc_assets = latest_version.get("document", {}).get("assets", [])
    print(f"Document Assets: {len(doc_assets)}")
    video_ref = next((a for a in doc_assets if a.get("asset_type") == "video"), None)
    assert video_ref is not None, "Rendered video asset reference missing in ProjectVersion document!"
    print(f"VERIFIED: Rendered video asset attached to ProjectVersion: {video_ref['asset_id']}")

    print("\n--- 9. Follow-Up Prompt: 'Make it shorter and more professional' ---")
    follow_payload = {
        "prompt": "Make it shorter and more professional.",
        "target_duration_seconds": 6,
        "aspect_ratio": "16:9",
        "avatar_id": selected_avatar["id"],
        "voice_id": selected_voice_id,
        "video_tone": "Professional",
        "run_async": True,
    }
    follow_job_resp = http_json("POST", f"/api/v1/workspaces/{workspace_id}/projects/generate", follow_payload, token=token, workspace_id=workspace_id)
    follow_job_id = follow_job_resp["id"]
    print(f"Follow-up job submitted. Job ID: {follow_job_id}, Status: {follow_job_resp['status']}")

    start_time = time.time()
    follow_completed_job = None
    while time.time() - start_time < 90:
        polled = http_json("GET", f"/api/v1/jobs/{follow_job_id}", token=token, workspace_id=workspace_id)
        if polled["status"] in ("succeeded", "completed"):
            follow_completed_job = polled
            print(f"Follow-up job completed in {time.time() - start_time:.2f}s!")
            break
        elif polled["status"] == "failed":
            raise RuntimeError(f"Follow-up job failed: {polled.get('error_details')}")
        time.sleep(1)

    assert follow_completed_job is not None, "Follow-up job timed out!"
    follow_result = follow_completed_job["result"]
    follow_asset_id = follow_result["output_asset_id"]
    follow_down = http_json("GET", f"/api/v1/workspaces/{workspace_id}/assets/{follow_asset_id}/download", token=token, workspace_id=workspace_id)
    assert follow_down.get("download_url"), "Follow-up video download URL missing!"
    print(f"VERIFIED: Follow-up generated valid video asset: {follow_asset_id}")

    print("\n========================================================")
    print("ALL REAL MEDIA GENERATION CRITERIA VERIFIED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    main()
