import uuid
import pytest
import httpx
from httpx import AsyncClient

from app.db.seeds import (
    ASSET_PIPER_LESSAC_PREVIEW_ID,
    ASSET_PIPER_DAVEFX_PREVIEW_ID,
    ASSET_PIPER_BRYCE_PREVIEW_ID,
    ASSET_PIPER_JOE_PREVIEW_ID,
    ASSET_PIPER_KRISTIN_PREVIEW_ID,
    ASSET_PIPER_JOHN_PREVIEW_ID,
    ASSET_PIPER_ALBA_PREVIEW_ID,
    ASSET_PIPER_SHARVARD_PREVIEW_ID,
    ASSET_PIPER_CLAUDE_PREVIEW_ID,
    ASSET_PIPER_THORSTEN_PREVIEW_ID,
    ASSET_PIPER_SIWIS_PREVIEW_ID,
    ASSET_PIPER_SERENA_PREVIEW_ID,
    ASSET_PIPER_FABER_PREVIEW_ID,
    ASSET_KOKORO_HEART_PREVIEW_ID,
    ASSET_KOKORO_EMMA_PREVIEW_ID,
    ASSET_KOKORO_DORA_PREVIEW_ID,
    ASSET_KOKORO_SIWIS_PREVIEW_ID,
    seed_canonical_presets,
)

VOICE_LESSAC_ID = "10000000-0000-0000-0000-000000000001"
VOICE_DAVEFX_ID = "10000000-0000-0000-0000-000000000002"
VOICE_ANNIE_MOCK_ID = "10000000-0000-0000-0000-000000000003"
VOICE_BRYCE_ID = "10000000-0000-0000-0000-000000000004"
VOICE_JOE_ID = "10000000-0000-0000-0000-000000000005"
VOICE_KRISTIN_ID = "10000000-0000-0000-0000-000000000006"
VOICE_JOHN_ID = "10000000-0000-0000-0000-000000000007"
VOICE_ALBA_ID = "10000000-0000-0000-0000-000000000008"
VOICE_SHARVARD_ID = "10000000-0000-0000-0000-000000000009"
VOICE_CLAUDE_ID = "10000000-0000-0000-0000-000000000010"
VOICE_THORSTEN_ID = "10000000-0000-0000-0000-000000000011"
VOICE_MONIKA_MOCK_ID = "10000000-0000-0000-0000-000000000012"
VOICE_SIWIS_ID = "10000000-0000-0000-0000-000000000013"
VOICE_SERENA_ID = "10000000-0000-0000-0000-000000000014"
VOICE_FABER_ID = "10000000-0000-0000-0000-000000000015"

VOICE_KOKORO_HEART_ID = "10000000-0000-0000-0000-000000000021"
VOICE_KOKORO_EMMA_ID = "10000000-0000-0000-0000-000000000022"
VOICE_KOKORO_DORA_ID = "10000000-0000-0000-0000-000000000023"
VOICE_KOKORO_SIWIS_ID = "10000000-0000-0000-0000-000000000024"

NEW_REAL_VOICES_MATRIX = [
    (VOICE_BRYCE_ID, str(ASSET_PIPER_BRYCE_PREVIEW_ID), "en_US-bryce-medium", "en"),
    (VOICE_JOE_ID, str(ASSET_PIPER_JOE_PREVIEW_ID), "en_US-joe-medium", "en"),
    (VOICE_KRISTIN_ID, str(ASSET_PIPER_KRISTIN_PREVIEW_ID), "en_US-kristin-medium", "en"),
    (VOICE_JOHN_ID, str(ASSET_PIPER_JOHN_PREVIEW_ID), "en_US-john-medium", "en"),
    (VOICE_ALBA_ID, str(ASSET_PIPER_ALBA_PREVIEW_ID), "en_GB-alba-medium", "en"),
    (VOICE_SHARVARD_ID, str(ASSET_PIPER_SHARVARD_PREVIEW_ID), "es_ES-sharvard-medium", "es"),
    (VOICE_CLAUDE_ID, str(ASSET_PIPER_CLAUDE_PREVIEW_ID), "es_MX-claude-high", "es"),
    (VOICE_THORSTEN_ID, str(ASSET_PIPER_THORSTEN_PREVIEW_ID), "de_DE-thorsten-medium", "de"),
    (VOICE_SIWIS_ID, str(ASSET_PIPER_SIWIS_PREVIEW_ID), "fr_FR-siwis-medium", "fr"),
    (VOICE_SERENA_ID, str(ASSET_PIPER_SERENA_PREVIEW_ID), "it_IT-serena-medium", "it"),
    (VOICE_FABER_ID, str(ASSET_PIPER_FABER_PREVIEW_ID), "pt_BR-faber-medium", "pt"),
]

KOKORO_REAL_VOICES_MATRIX = [
    (VOICE_KOKORO_HEART_ID, str(ASSET_KOKORO_HEART_PREVIEW_ID), "af_heart", "en"),
    (VOICE_KOKORO_EMMA_ID, str(ASSET_KOKORO_EMMA_PREVIEW_ID), "bf_emma", "en"),
    (VOICE_KOKORO_DORA_ID, str(ASSET_KOKORO_DORA_PREVIEW_ID), "ef_dora", "es"),
    (VOICE_KOKORO_SIWIS_ID, str(ASSET_KOKORO_SIWIS_PREVIEW_ID), "ff_siwis", "fr"),
]


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


@pytest.mark.asyncio
async def test_voice_preview_piper_lessac_success(async_client: AsyncClient):
    token, ws_id = await _setup_user_workspace(async_client, "Voice Preview User")
    resp = await async_client.get(
        f"/api/v1/voices/{VOICE_LESSAC_ID}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["voice_id"] == VOICE_LESSAC_ID
    assert data["preview_asset_id"] == str(ASSET_PIPER_LESSAC_PREVIEW_ID)
    assert data["provider"] == "piper"
    assert data["preview_url"] is not None
    assert "http" in data["preview_url"]

    # Verify that fetching the preview_url directly works
    async with httpx.AsyncClient() as direct_client:
        audio_resp = await direct_client.get(data["preview_url"])
        assert audio_resp.status_code == 200
        assert "audio/wav" in audio_resp.headers.get("content-type", "")
        assert len(audio_resp.content) > 1000


@pytest.mark.asyncio
async def test_voice_preview_piper_davefx_success(async_client: AsyncClient):
    token, ws_id = await _setup_user_workspace(async_client, "Voice Preview ES User")
    resp = await async_client.get(
        f"/api/v1/voices/{VOICE_DAVEFX_ID}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["voice_id"] == VOICE_DAVEFX_ID
    assert data["preview_asset_id"] == str(ASSET_PIPER_DAVEFX_PREVIEW_ID)
    assert data["provider"] == "piper"
    assert data["preview_url"] is not None


@pytest.mark.parametrize("voice_id,expected_asset_id,expected_model,expected_lang", NEW_REAL_VOICES_MATRIX)
@pytest.mark.asyncio
async def test_all_11_new_piper_voices_preview_success(
    async_client: AsyncClient,
    voice_id: str,
    expected_asset_id: str,
    expected_model: str,
    expected_lang: str,
):
    token, ws_id = await _setup_user_workspace(async_client, f"Voice_{voice_id[:6]}")
    
    # 1. Fetch voice metadata
    get_resp = await async_client.get(
        f"/api/v1/voices/{voice_id}",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert get_resp.status_code == 200, get_resp.text
    v_data = get_resp.json()
    assert v_data["id"] == voice_id
    assert v_data["provider"] == "piper"
    assert v_data["provider_reference"] == expected_model
    assert v_data["language"] == expected_lang
    assert v_data["status"] == "ready"
    assert v_data["preview_asset_id"] == expected_asset_id
    assert v_data["preview_url"] is not None

    # 2. Fetch preview endpoint directly
    prev_resp = await async_client.get(
        f"/api/v1/voices/{voice_id}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert prev_resp.status_code == 200, prev_resp.text
    p_data = prev_resp.json()
    assert p_data["voice_id"] == voice_id
    assert p_data["preview_asset_id"] == expected_asset_id
    assert p_data["provider"] == "piper"
    assert p_data["preview_url"] is not None

    # 3. Direct HTTP fetch of preview audio from MinIO
    async with httpx.AsyncClient() as direct_client:
        audio_resp = await direct_client.get(p_data["preview_url"])
        assert audio_resp.status_code == 200
        assert "audio/wav" in audio_resp.headers.get("content-type", "")
        assert len(audio_resp.content) > 10000


@pytest.mark.parametrize("voice_id,expected_asset_id,expected_ref,expected_lang", KOKORO_REAL_VOICES_MATRIX)
@pytest.mark.asyncio
async def test_all_4_kokoro_voices_preview_success(
    async_client: AsyncClient,
    voice_id: str,
    expected_asset_id: str,
    expected_ref: str,
    expected_lang: str,
):
    token, ws_id = await _setup_user_workspace(async_client, f"KokoroVoice_{voice_id[-4:]}")

    # 1. Fetch voice metadata
    get_resp = await async_client.get(
        f"/api/v1/voices/{voice_id}",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert get_resp.status_code == 200, get_resp.text
    v_data = get_resp.json()
    assert v_data["id"] == voice_id
    assert v_data["provider"] == "kokoro"
    assert v_data["provider_reference"] == expected_ref
    assert v_data["language"] == expected_lang
    assert v_data["status"] == "ready"
    assert v_data["preview_asset_id"] == expected_asset_id
    assert v_data["preview_url"] is not None

    # 2. Fetch preview endpoint directly
    prev_resp = await async_client.get(
        f"/api/v1/voices/{voice_id}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert prev_resp.status_code == 200, prev_resp.text
    p_data = prev_resp.json()
    assert p_data["voice_id"] == voice_id
    assert p_data["preview_asset_id"] == expected_asset_id
    assert p_data["provider"] == "kokoro"
    assert p_data["preview_url"] is not None

    # 3. Direct HTTP fetch of preview audio from MinIO
    async with httpx.AsyncClient() as direct_client:
        audio_resp = await direct_client.get(p_data["preview_url"])
        assert audio_resp.status_code == 200
        assert "audio/wav" in audio_resp.headers.get("content-type", "")
        assert len(audio_resp.content) > 10000


@pytest.mark.asyncio
async def test_voice_preview_mock_voice_unavailable(async_client: AsyncClient):
    token, ws_id = await _setup_user_workspace(async_client, "Mock Voice Tester")

    # Check Annie (slot 3)
    resp = await async_client.get(
        f"/api/v1/voices/{VOICE_ANNIE_MOCK_ID}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert resp.status_code == 404
    err_msg = resp.json().get("error", {}).get("message", "")
    assert "mock preset" in err_msg.lower() or "not have an audio preview" in err_msg.lower()

    # Check Monika Sogam (slot 12)
    resp_monika = await async_client.get(
        f"/api/v1/voices/{VOICE_MONIKA_MOCK_ID}/preview",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert resp_monika.status_code == 404


@pytest.mark.asyncio
async def test_list_voices_includes_all_real_previews(async_client: AsyncClient):
    token, ws_id = await _setup_user_workspace(async_client, "List Voices Tester")
    resp = await async_client.get(
        "/api/v1/voices",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
    )
    assert resp.status_code == 200
    voices = resp.json()
    assert len(voices) >= 19

    by_id = {v["id"]: v for v in voices}

    # Check Lessac and Davefx
    assert by_id[VOICE_LESSAC_ID]["preview_url"] is not None
    assert by_id[VOICE_DAVEFX_ID]["preview_url"] is not None

    # Check all 11 new real Piper voices
    for v_id, _, _, _ in NEW_REAL_VOICES_MATRIX:
        assert by_id[v_id]["preview_url"] is not None
        assert by_id[v_id]["provider"] == "piper"

    # Check all 4 new real Kokoro voices
    for k_id, _, _, _ in KOKORO_REAL_VOICES_MATRIX:
        assert by_id[k_id]["preview_url"] is not None
        assert by_id[k_id]["provider"] == "kokoro"

    # Check mock voices have no preview
    assert by_id[VOICE_ANNIE_MOCK_ID]["preview_url"] is None
    assert by_id[VOICE_MONIKA_MOCK_ID]["preview_url"] is None


@pytest.mark.asyncio
async def test_seed_canonical_presets_idempotency():
    # Calling seed a second/third time must return the exact canonical count without error
    c1 = await seed_canonical_presets()
    c2 = await seed_canonical_presets()
    assert c1 == c2
    assert c1 == 19



