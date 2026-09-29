"""Tests for Avatar visual assets, signed preview URLs, looks, and workspace scoping."""

import uuid
import pytest
from httpx import AsyncClient
import httpx
from app.storage.s3 import get_storage_provider


@pytest.mark.asyncio
async def test_avatar_catalog_signed_preview_urls_and_looks(async_client: AsyncClient):
    # 1. Log in as development user
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "dev@heyzen.ai", "password": "DevPassword123!"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["tokens"]["access_token"]
    ws_id = "22222222-2222-2222-2222-222222222222"
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # 2. Query GET /api/v1/avatars
    res = await async_client.get("/api/v1/avatars", headers=headers)
    assert res.status_code == 200
    avatars = res.json()
    assert len(avatars) >= 5

    # 3. Find Default Presenter
    default_pres = next((a for a in avatars if a.get("provider_reference") == "default-presenter"), None)
    assert default_pres is not None
    assert default_pres["name"] == "Default Presenter"
    assert default_pres["preview_url"] is not None
    assert "heyzen-assets" in default_pres["preview_url"]
    assert len(default_pres["looks"]) >= 3

    # Verify looks have signed preview_urls
    for look in default_pres["looks"]:
        assert look["preview_url"] is not None
        assert "heyzen-assets" in look["preview_url"]

    # 4. Verify GET /api/v1/avatars/{avatar_id} returns preview_url and looks
    avatar_id = default_pres["id"]
    get_res = await async_client.get(f"/api/v1/avatars/{avatar_id}", headers=headers)
    assert get_res.status_code == 200
    single_av = get_res.json()
    assert single_av["id"] == avatar_id
    assert single_av["preview_url"] is not None
    assert len(single_av["looks"]) >= 3

    # 5. Verify GET /api/v1/avatars/{avatar_id}/looks returns looks with preview_url
    looks_res = await async_client.get(f"/api/v1/avatars/{avatar_id}/looks", headers=headers)
    assert looks_res.status_code == 200
    looks = looks_res.json()
    assert len(looks) >= 3
    for l in looks:
        assert l["preview_url"] is not None


@pytest.mark.asyncio
async def test_all_canonical_avatars_have_valid_visual_assets(async_client: AsyncClient):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "dev@heyzen.ai", "password": "DevPassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["tokens"]["access_token"]
    ws_id = "22222222-2222-2222-2222-222222222222"
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    res = await async_client.get("/api/v1/avatars", headers=headers)
    assert res.status_code == 200
    avatars = res.json()

    expected_avatars = [
        ("default-presenter", "Default Presenter"),
        ("annie", "Annie - Studio Presenter"),
        ("rasmus", "Rasmus - Executive"),
        ("daniel", "Daniel - Modern Creator"),
        ("sophia", "Sophia - Creative Director"),
    ]

    preview_urls = []
    asset_ids = []

    async with httpx.AsyncClient(timeout=10.0) as http_fetcher:
        for pref, expected_name in expected_avatars:
            matched = next((a for a in avatars if a.get("provider_reference") == pref), None)
            assert matched is not None, f"Missing avatar with provider_reference={pref}"
            assert matched["name"] == expected_name
            p_url = matched.get("preview_url")
            assert p_url is not None, f"Avatar {expected_name} has no preview_url"
            assert len(p_url) > 10
            preview_urls.append(p_url)
            asset_ids.append(matched["preview_asset_id"])

            # Verify image is a real JPEG (>50KB, not 3445 synthetic)
            r = await http_fetcher.get(p_url)
            assert r.status_code == 200
            assert r.headers.get("Content-Type") == "image/jpeg"
            assert len(r.content) > 50000, f"Asset for {expected_name} is too small ({len(r.content)} bytes)"
            assert r.content.startswith(b"\xff\xd8\xff"), f"Asset for {expected_name} is not JPEG"

    # All five avatars must have distinct preview assets and URLs
    assert len(set(preview_urls)) == 5
    assert len(set(asset_ids)) == 5


@pytest.mark.asyncio
async def test_seed_preserves_real_avatar_assets():
    """Verify that stored avatar objects in MinIO are legitimate JPEGs and not synthetic."""
    storage = get_storage_provider()
    
    canonical_keys = [
        ("Default Presenter", "workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000101/default_presenter.jpg"),
        ("Annie - Studio Presenter", "workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000102/annie_studio_presenter.jpg"),
        ("Rasmus - Executive", "workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000103/rasmus_executive.jpg"),
        ("Daniel - Modern Creator", "workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000104/daniel_modern_creator.jpg"),
        ("Sophia - Creative Director", "workspaces/00000000-0000-0000-0000-000000000001/assets/20000000-0000-0000-0000-000000000105/sophia_creative_director.jpg"),
    ]

    for name, key in canonical_keys:
        assert storage.object_exists(key), f"Key {key} does not exist for {name}"
        meta = storage.get_object_metadata(key)
        assert meta is not None, f"Metadata missing for {key}"
        assert meta["content_type"] == "image/jpeg"
        assert meta["size_bytes"] > 50000, f"Size for {name} is synthetic: {meta['size_bytes']}"
