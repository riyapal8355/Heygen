"""Comprehensive API and Swagger Smoke Testing Suite for HeyZen Platform.

Tests public endpoints, Swagger UI, ReDoc, OpenAPI schemas across all required domains
(Projects, Studio, Media, Audio, AI, Rendering, Jobs, Webhooks, API Keys, Developer),
authentication lifecycle, unauthorized request rejection, Studio OCC document saving,
and developer endpoint operations.
"""

import json
import urllib.request
import urllib.error
import uuid

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, data=None, token=None, extra_headers=None, expected_status=200):
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": "SmokeTester/1.0"}
    if extra_headers:
        headers.update(extra_headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = resp.status
            resp_body = resp.read().decode("utf-8")
            content_type = resp.headers.get_content_type()
            if "json" in content_type and resp_body:
                parsed = json.loads(resp_body)
            else:
                parsed = resp_body
            assert status_code == expected_status, f"Expected {expected_status}, got {status_code}"
            return status_code, parsed
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        if e.code == expected_status:
            parsed = json.loads(err_body) if ("json" in e.headers.get_content_type() and err_body) else err_body
            return e.code, parsed
        print(f"FAILED {method} {path} -> HTTP {e.code}: {err_body}")
        raise

def run_smoke_tests():
    print("=" * 70)
    print("Phase 45.6 — Complete Swagger & API Smoke Test Suite")
    print("=" * 70)

    # 1. Base & Documentation Endpoints
    print("\n[1/7] Testing Base & Documentation Endpoints...")
    status, h = request("GET", "/health")
    print(f"  GET /health: {status} (status={h.get('status')}, app={h.get('app')})")
    assert h.get("status") == "ok"

    status, r = request("GET", "/ready")
    print(f"  GET /ready: {status} (status={r.get('status')})")
    assert r.get("status") == "ready"

    status, docs_html = request("GET", "/docs")
    print(f"  GET /docs: {status} (Swagger UI HTML loaded, size={len(docs_html)} bytes)")
    assert "swagger-ui" in docs_html.lower()

    status, redoc_html = request("GET", "/redoc")
    print(f"  GET /redoc: {status} (ReDoc HTML loaded, size={len(redoc_html)} bytes)")
    assert "redoc" in redoc_html.lower()

    status, schema = request("GET", "/openapi.json")
    print(f"  GET /openapi.json: {status} (OpenAPI {schema.get('openapi')}, paths={len(schema.get('paths', {}))})")

    # 2. Verify OpenAPI Domain Coverage across required groups
    print("\n[2/7] Verifying OpenAPI Schema Domain Coverage...")
    required_domains = [
        "Projects",
        "Studio",
        "Media",
        "Audio",
        "AI",
        "Rendering",
        "Jobs",
        "Webhooks",
        "API Keys",
        "Developer",
    ]

    all_tags = set()
    paths = schema.get("paths", {})
    for path, path_item in paths.items():
        for method, op in path_item.items():
            if isinstance(op, dict) and "tags" in op:
                all_tags.update(op["tags"])

    for domain in required_domains:
        assert domain in all_tags, f"Missing required domain tag in OpenAPI: '{domain}'"
        matching_ops = []
        for path, path_item in paths.items():
            for method, op in path_item.items():
                if isinstance(op, dict) and domain in op.get("tags", []):
                    matching_ops.append(f"{method.upper()} {path}")
        print(f"  Tag '{domain:12s}': VERIFIED ({len(matching_ops)} operations, e.g. {matching_ops[0]})")

    # 3. Security & Protected Route Guard Verification
    print("\n[3/7] Testing Security Guards (Unauthenticated Request Rejection)...")
    status, err = request("GET", "/api/v1/auth/me", expected_status=401)
    print(f"  GET /api/v1/auth/me without token: {status} UNAUTHORIZED (code={err.get('error', {}).get('code')})")
    assert "UNAUTHORIZED" in err.get("error", {}).get("code", "")

    status, err = request("GET", "/api/v1/workspaces", expected_status=401)
    print(f"  GET /api/v1/workspaces without token: {status} UNAUTHORIZED (code={err.get('error', {}).get('code')})")
    assert "UNAUTHORIZED" in err.get("error", {}).get("code", "")

    # 4. Authentication Flow (Signup, Profile, Refresh, Logout, Login)
    print("\n[4/7] Testing Full Authentication Lifecycle...")
    test_email = f"smoketest_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "SmokeTestPassword123!"
    test_name = "Swagger Smoke Tester"

    status, auth = request("POST", "/api/v1/auth/signup", {
        "email": test_email,
        "password": test_password,
        "display_name": test_name,
    }, expected_status=201)
    token = auth["tokens"]["access_token"]
    user_id = auth["user"]["id"]
    ws = auth.get("workspace")
    workspace_id = ws["id"] if ws else None
    print(f"  POST /api/v1/auth/signup: {status} (user_id={user_id}, ws={workspace_id})")

    status, me = request("GET", "/api/v1/auth/me", token=token)
    print(f"  GET /api/v1/auth/me: {status} (email={me['user']['email']}, workspaces={len(me.get('workspaces', []))})")
    if not workspace_id and me.get("workspaces"):
        workspace_id = me["workspaces"][0]["id"]

    # Refresh
    status, refreshed = request("POST", "/api/v1/auth/refresh", {
        "refresh_token": "dummy_will_fallback_or_succeed"
    }, token=token, expected_status=401)  # invalid refresh token without cookie returns 401 fail-safe
    print(f"  POST /api/v1/auth/refresh (invalid token validation): {status} (correctly rejected)")

    # Logout
    status, logout_resp = request("POST", "/api/v1/auth/logout", token=token)
    print(f"  POST /api/v1/auth/logout: {status} (status={logout_resp.get('status')}, msg='{logout_resp.get('message')}')")
    assert logout_resp.get("status") == "ok"

    # Re-login
    status, login_resp = request("POST", "/api/v1/auth/login", {
        "email": test_email,
        "password": test_password,
    })
    token = login_resp["tokens"]["access_token"]
    print(f"  POST /api/v1/auth/login: {status} (new access token issued)")

    # 5. Workspace Context, Folders & Path Parameter Validation
    print("\n[5/8] Testing Workspace Context, Folders & Path Parameter Validation...")
    # 5a. Create a real folder in the workspace
    status, f_created = request("POST", f"/api/v1/workspaces/{workspace_id}/folders", {
        "name": "Integration Test Folder",
    }, token=token, expected_status=201)
    folder_id = f_created["id"]
    print(f"  POST /workspaces/{workspace_id}/folders: {status} (folder_id={folder_id})")

    # 5b. Retrieve folder with valid workspace_id and folder_id (The exact route reported in Phase 45.7)
    status, f_fetched = request("GET", f"/api/v1/workspaces/{workspace_id}/folders/{folder_id}", token=token)
    print(f"  GET /workspaces/{workspace_id}/folders/{folder_id}: {status} (name='{f_fetched['name']}')")
    assert f_fetched["id"] == folder_id

    # 5c. Test with matching X-Workspace-ID header and URL path
    status, f_matched = request(
        "GET",
        f"/api/v1/workspaces/{workspace_id}/folders/{folder_id}",
        token=token,
        extra_headers={"X-Workspace-ID": str(workspace_id)},
    )
    print(f"  GET with matching X-Workspace-ID header: {status} OK")

    # 5d. Test with mismatched X-Workspace-ID header (Security Guard)
    bogus_ws = str(uuid.uuid4())
    status, err_mismatch = request(
        "GET",
        f"/api/v1/workspaces/{workspace_id}/folders/{folder_id}",
        token=token,
        extra_headers={"X-Workspace-ID": bogus_ws},
        expected_status=403,
    )
    print(f"  GET with mismatched X-Workspace-ID header: {status} (code={err_mismatch.get('error', {}).get('code')})")
    assert err_mismatch.get("error", {}).get("code") == "WORKSPACE_MISMATCH"

    # 5e. Test literal unreplaced placeholder rejected cleanly
    status, err_literal = request(
        "GET",
        f"/api/v1/workspaces/{{workspace_id}}/folders/{folder_id}",
        token=token,
        expected_status=404,
    )
    print(f"  GET with literal '{{workspace_id}}' placeholder: {status} (code={err_literal.get('error', {}).get('code')})")
    assert err_literal.get("error", {}).get("code") == "WORKSPACE_INVALID_ID"

    # 5f. Verify Development Seed Fixture accessibility
    DEV_EMAIL = "dev@heyzen.ai"
    DEV_PASSWORD = "DevPassword123!"
    DEV_WS_ID = "22222222-2222-2222-2222-222222222222"
    DEV_FOLDER_ID = "33333333-3333-3333-3333-333333333333"

    status, dev_login = request("POST", "/api/v1/auth/login", {
        "email": DEV_EMAIL,
        "password": DEV_PASSWORD,
    })
    dev_token = dev_login["tokens"]["access_token"]
    print(f"  POST /api/v1/auth/login (dev seed user): {status} OK")

    status, dev_folder = request("GET", f"/api/v1/workspaces/{DEV_WS_ID}/folders/{DEV_FOLDER_ID}", token=dev_token)
    print(f"  GET /workspaces/{DEV_WS_ID}/folders/{DEV_FOLDER_ID} (dev fixture): {status} (name='{dev_folder['name']}')")
    assert dev_folder["id"] == DEV_FOLDER_ID

    # 6. Studio Multi-Layer Document Lifecycle & OCC Versioning
    print("\n[6/8] Testing Studio Document Model & OCC Snapshot Persistence...")
    status, proj = request("POST", f"/api/v1/workspaces/{workspace_id}/projects", {
        "title": "Smoke Test Studio Project",
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
    }, token=token, expected_status=201)
    project_id = proj["id"]
    print(f"  POST /projects (create): {status} (project_id={project_id})")

    status, versions = request("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions", token=token)
    print(f"  GET /projects/{project_id}/versions: {status} (initial versions={len(versions)})")
    initial_rev = versions[0]["revision"]

    # Construct rich ProjectDocumentV1 testing all canvas layer types, z-ordering, locking, visibility
    scene_id = f"scene_{uuid.uuid4().hex[:8]}"
    text_layer_id = f"layer_txt_{uuid.uuid4().hex[:8]}"
    media_layer_id = f"layer_media_{uuid.uuid4().hex[:8]}"
    element_layer_id = f"layer_elem_{uuid.uuid4().hex[:8]}"
    audio_track_id = f"audio_{uuid.uuid4().hex[:8]}"

    studio_doc = {
        "version": 1,
        "settings": {
            "aspect_ratio": "16:9",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "total_duration": 10.0,
            "captions": {
                "enabled": True,
                "style": {
                    "font_family": "Arial",
                    "font_size": 36,
                    "font_weight": "bold",
                    "color": "#FFFFFF",
                    "background_color": "#000000",
                    "background_opacity": 0.7,
                    "position": "bottom",
                    "alignment": "center",
                    "z_index": 10,
                },
            },
        },
        "scenes": [
            {
                "id": scene_id,
                "sequence": 1,
                "duration": 10.0,
                "transition": {
                    "type": "fade",
                    "duration": 0.5,
                },
                "background": {"type": "color", "value": "#0F172A"},
                "layers": [
                    {
                        "id": media_layer_id,
                        "type": "image",
                        "name": "Background Backdrop",
                        "start_time": 0.0,
                        "end_time": 10.0,
                        "enabled": True,
                        "locked": True,
                        "z_index": 1,
                        "transform": {"x": 960, "y": 540, "scale_x": 1.0, "scale_y": 1.0, "rotation": 0.0},
                        "content": {"url": "https://example.com/backdrop.jpg"},
                    },
                    {
                        "id": element_layer_id,
                        "type": "shape",
                        "name": "Accent Banner",
                        "start_time": 0.0,
                        "end_time": 10.0,
                        "enabled": True,
                        "locked": False,
                        "z_index": 2,
                        "transform": {"x": 960, "y": 300, "scale_x": 1.0, "scale_y": 1.0, "rotation": 0.0},
                        "content": {"shape_type": "rectangle", "color": "#3B82F6"},
                    },
                    {
                        "id": text_layer_id,
                        "type": "text",
                        "name": "Headline",
                        "start_time": 1.0,
                        "end_time": 9.0,
                        "enabled": True,
                        "locked": False,
                        "z_index": 3,
                        "transform": {"x": 960, "y": 300, "scale_x": 1.0, "scale_y": 1.0, "rotation": 0.0},
                        "content": {"text": "HeyZen Autonomous Video Studio", "font_size": 48, "color": "#FFFFFF"},
                    },
                ],
                "subtitles": [
                    {"id": 1, "start": 1.0, "end": 4.0, "text": "Welcome to HeyZen Studio", "words": []},
                ],
            },
        ],
        "audio_tracks": [
            {
                "id": audio_track_id,
                "name": "Background Score",
                "volume": 0.7,
                "start_time": 0.0,
                "duration": 10.0,
                "fade_in_duration": 1.0,
                "fade_out_duration": 1.0,
                "loop": True,
                "muted": False,
            },
        ],
    }

    # Save OCC Version
    status, saved_version = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
        {
            "expected_revision": initial_rev,
            "document": studio_doc,
            "source": "manual",
        },
        token=token,
        expected_status=201,
    )
    print(f"  POST /projects/{project_id}/versions (OCC save): {status} (new revision={saved_version['revision']})")

    # Fetch version snapshot
    version_id = saved_version["id"]
    status, v_fetch = request("GET", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{version_id}", token=token)
    print(f"  GET /projects/{project_id}/versions/{version_id}: {status} (revision={v_fetch['revision']})")

    # Pre-flight Timeline Validation
    status, diag = request("POST", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/validate", token=token)
    print(f"  POST /projects/{project_id}/validate: {status} (valid={diag.get('valid')}, scenes={diag.get('total_scenes')})")

    # 7. Developer APIs (API Keys & Webhooks)
    print("\n[7/8] Testing Developer APIs (API Keys & Webhooks)...")
    # API Key creation
    status, key_resp = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/developer/api-keys",
        {
            "name": "Integration Test Key",
            "environment": "sandbox",
            "permissions": "full",
        },
        token=token,
        expected_status=201,
    )
    api_key_id = key_resp["id"]
    print(f"  POST /developer/api-keys: {status} (key_id={api_key_id}, prefix={key_resp.get('prefix')})")

    status, keys_list = request("GET", f"/api/v1/workspaces/{workspace_id}/developer/api-keys", token=token)
    print(f"  GET /developer/api-keys: {status} (total={keys_list.get('total')})")

    # Webhook creation
    status, wh_resp = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/developer/webhooks",
        {
            "url": "https://example.com/webhook/receiver",
            "events": ["job.succeeded", "job.failed"],
            "description": "Integration test webhook",
        },
        token=token,
        expected_status=201,
    )
    webhook_id = wh_resp["id"]
    print(f"  POST /developer/webhooks: {status} (webhook_id={webhook_id}, url={wh_resp.get('url')})")

    # Test Webhook Ping
    status, test_wh = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/test",
        token=token,
    )
    print(f"  POST /developer/webhooks/{webhook_id}/test: {status} (status={test_wh.get('status')}, event_id={test_wh.get('event_id')})")
    assert test_wh.get("status") == "enqueued"

    # Cleanup Developer resources
    status, _ = request("DELETE", f"/api/v1/workspaces/{workspace_id}/developer/api-keys/{api_key_id}", token=token)
    print(f"  DELETE /developer/api-keys/{api_key_id}: {status} (revoked)")

    status, _ = request("DELETE", f"/api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}", token=token, expected_status=204)
    print(f"  DELETE /developer/webhooks/{webhook_id}: {status} (deleted)")

    # 8. Safe Read-Only Catalogs & Clean Teardown
    print("\n[8/8] Testing Catalogs & Clean Teardown...")
    status, voices = request("GET", "/api/v1/voices", token=token)
    print(f"  GET /api/v1/voices: {status} (catalog voices={len(voices)})")

    status, avatars = request("GET", "/api/v1/avatars", token=token)
    print(f"  GET /api/v1/avatars: {status} (catalog avatars={len(avatars)})")

    status, templates = request("GET", "/api/v1/templates", token=token)
    print(f"  GET /api/v1/templates: {status} (catalog templates={len(templates)})")

    status, _ = request("DELETE", f"/api/v1/workspaces/{workspace_id}/projects/{project_id}", token=token, expected_status=204)
    print(f"  DELETE /projects/{project_id}: {status} (soft-deleted)")

    print("\n" + "=" * 70)
    print("ALL SWAGGER & API SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_smoke_tests()
