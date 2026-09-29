"""Test suite for Voice catalog management, filtering, asset binding, and workspace isolation."""

import uuid
import pytest
from httpx import AsyncClient


async def _setup_user_workspace(async_client: AsyncClient, name: str) -> tuple[str, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspace_id = ws_resp.json()[0]["id"]
    return token, workspace_id


async def _create_test_asset(async_client: AsyncClient, token: str, ws_id: str, filename: str = "sample.wav") -> str:
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_filename": filename, "mime_type": "audio/wav", "size_bytes": 4096, "asset_type": "audio"},
    )
    assert resp.status_code == 201
    return resp.json()["asset_id"]


@pytest.mark.asyncio
async def test_voice_crud_and_filtering(async_client: AsyncClient):
    """Verify voice creation with audio preview, filtering by language/gender, and soft-delete."""
    token, ws_id = await _setup_user_workspace(async_client, "Voice Admin")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    preview_asset_id = await _create_test_asset(async_client, token, ws_id, "voice_sample.wav")

    # 1. Create voices
    v1_resp = await async_client.post(
        "/api/v1/voices",
        headers=headers,
        json={
            "name": "Marcus Calm",
            "language": "en",
            "gender": "male",
            "voice_type": "preset",
            "preview_asset_id": preview_asset_id,
        },
    )
    assert v1_resp.status_code == 201
    v1_id = v1_resp.json()["id"]

    v2_resp = await async_client.post(
        "/api/v1/voices",
        headers=headers,
        json={
            "name": "Elena Warm",
            "language": "es",
            "gender": "female",
            "voice_type": "cloned",
        },
    )
    assert v2_resp.status_code == 201

    # 2. List all (verify workspace voices exist alongside public catalog)
    all_resp = await async_client.get("/api/v1/voices", headers=headers)
    ws_all = [v for v in all_resp.json() if v["workspace_id"] == ws_id]
    assert len(ws_all) == 2

    # 3. Filter by language
    es_resp = await async_client.get("/api/v1/voices", headers=headers, params={"language": "es"})
    ws_es = [v for v in es_resp.json() if v["workspace_id"] == ws_id]
    assert len(ws_es) == 1
    assert ws_es[0]["name"] == "Elena Warm"

    # 4. Filter by gender
    male_resp = await async_client.get("/api/v1/voices", headers=headers, params={"gender": "male"})
    ws_male = [v for v in male_resp.json() if v["workspace_id"] == ws_id]
    assert len(ws_male) == 1
    assert ws_male[0]["name"] == "Marcus Calm"

    # 5. Update voice
    upd_resp = await async_client.patch(
        f"/api/v1/voices/{v1_id}",
        headers=headers,
        json={"name": "Marcus Super Calm", "description": "Soothing narration tone"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Marcus Super Calm"

    # 6. Soft-delete voice
    del_resp = await async_client.delete(f"/api/v1/voices/{v1_id}", headers=headers)
    assert del_resp.status_code == 204

    # 7. Excluded after delete
    get_after = await async_client.get(f"/api/v1/voices/{v1_id}", headers=headers)
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_voice_name_rejected(async_client: AsyncClient):
    """Verify duplicate voice names in same workspace trigger 409 Conflict."""
    token, ws_id = await _setup_user_workspace(async_client, "Dup Voice User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    r1 = await async_client.post("/api/v1/voices", headers=headers, json={"name": "Duplicate Voice"})
    assert r1.status_code == 201

    r2 = await async_client.post("/api/v1/voices", headers=headers, json={"name": "Duplicate Voice"})
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "VOICE_NAME_EXISTS"


@pytest.mark.asyncio
async def test_voice_cross_workspace_asset_and_isolation(async_client: AsyncClient):
    """Verify cross-workspace asset linking and tenant isolation for voices."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Voice Tenant A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Voice Tenant B")

    asset_b_id = await _create_test_asset(async_client, token_b, ws_b, "audio_b.wav")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-ID": ws_a}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}

    # Cross-workspace asset rejected
    bad_resp = await async_client.post(
        "/api/v1/voices",
        headers=headers_a,
        json={"name": "Cross Voice", "preview_asset_id": asset_b_id},
    )
    assert bad_resp.status_code == 404
    assert bad_resp.json()["error"]["code"] == "ASSET_NOT_FOUND"

    # Create legitimate voice in A
    v_a = await async_client.post("/api/v1/voices", headers=headers_a, json={"name": "Voice A"})
    assert v_a.status_code == 201
    v_a_id = v_a.json()["id"]

    # User B cannot access Voice A
    get_b = await async_client.get(f"/api/v1/voices/{v_a_id}", headers=headers_b)
    assert get_b.status_code == 404
