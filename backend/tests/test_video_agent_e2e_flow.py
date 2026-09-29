import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_video_agent_e2e_generation_with_real_avatar_and_workspace():
    """End-to-end verification of Video Agent prompt-to-project generation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login with seeded dev credentials
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "dev@heyzen.ai",
            "password": "DevPassword123!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_data = login_resp.json()
        token = login_data["tokens"]["access_token"]
        workspace_id = login_data["workspace"]["id"]
        assert workspace_id == "22222222-2222-2222-2222-222222222222"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": workspace_id,
        }

        # 2. Query available avatars in the workspace
        avatars_resp = await client.get("/api/v1/avatars", headers=headers)
        assert avatars_resp.status_code == 200
        avatars = avatars_resp.json()
        assert len(avatars) >= 5
        annie = next((a for a in avatars if "annie" in a["name"].lower()), None)
        assert annie is not None, "Annie avatar must exist in catalog"
        assert annie["id"] == "30000000-0000-0000-0000-000000000002"

        # 3. Call projects/generate with real avatar ID and workspace
        gen_payload = {
            "prompt": "Create a high-impact promotional video for our AI video platform",
            "target_duration_seconds": 30,
            "aspect_ratio": "16:9",
            "avatar_id": annie["id"],
            "voice_id": "en_US-lessac-medium",
            "video_tone": "Professional",
            "auto_synthesize_speech": False,
            "run_async": False,
        }

        gen_resp = await client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/generate",
            headers=headers,
            json=gen_payload
        )
        assert gen_resp.status_code == 201, f"Generate failed: {gen_resp.text}"
        project = gen_resp.json()
        assert project["id"] is not None
        assert project["workspace_id"] == workspace_id
        project_id = project["id"]

        # 4. Verify ProjectVersion and Scenes were properly persisted
        versions_resp = await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/versions",
            headers=headers
        )
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert len(versions) >= 1
        doc = versions[0]["document"]
        assert "scenes" in doc
        scenes = doc["scenes"]
        assert len(scenes) >= 1
        for sc in scenes:
            assert sc["avatar"]["avatar_id"] == annie["id"]
            assert sc["speech"]["voice_id"] == "en_US-lessac-medium"

        # 5. Verify Workspace Isolation: another workspace cannot access the generated project
        other_workspace_id = "33333333-3333-3333-3333-333333333333"
        other_headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": other_workspace_id,
        }
        forbidden_resp = await client.get(
            f"/api/v1/workspaces/{other_workspace_id}/projects/{project_id}",
            headers=other_headers
        )
        assert forbidden_resp.status_code in (403, 404)
