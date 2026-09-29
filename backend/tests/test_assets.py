"""Test suite for Asset upload intents, MinIO confirmation, signed downloads, and workspace isolation."""

import uuid
import pytest
from httpx import AsyncClient

from app.storage.s3 import get_storage_provider


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
async def test_create_upload_intent_and_storage_key_isolation(async_client: AsyncClient):
    """Verify upload intent registers pending asset and generates workspace-isolated signed URL."""
    token, ws_id = await _setup_user_workspace(async_client, "Asset Uploader")
    headers = {"Authorization": f"Bearer {token}"}

    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers=headers,
        json={
            "original_filename": "avatar_portrait.png",
            "mime_type": "image/png",
            "size_bytes": 10240,
            "asset_type": "image",
            "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    )
    assert intent_resp.status_code == 201
    data = intent_resp.json()
    assert data["asset_id"] is not None
    assert f"workspaces/{ws_id}/assets/{data['asset_id']}/avatar_portrait.png" in data["storage_key"]
    assert "signed_upload_url" in data
    assert data["expires_in_seconds"] == 900
    assert data["required_headers"]["Content-Type"] == "image/png"

    # Asset starts in pending_upload status
    get_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/assets/{data['asset_id']}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    asset_meta = get_resp.json()
    assert asset_meta["status"] == "pending_upload"
    assert asset_meta["size_bytes"] == 10240


@pytest.mark.asyncio
async def test_confirm_upload_missing_object_rejected(async_client: AsyncClient):
    """Verify confirmation fails with 409 if binary object has not been uploaded to storage."""
    token, ws_id = await _setup_user_workspace(async_client, "Unconfirmed Uploader")
    headers = {"Authorization": f"Bearer {token}"}

    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers=headers,
        json={
            "original_filename": "phantom_video.mp4",
            "mime_type": "video/mp4",
            "asset_type": "video",
        },
    )
    asset_id = intent_resp.json()["asset_id"]

    # Attempt confirm without putting object to storage
    confirm_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/confirm",
        headers=headers,
    )
    assert confirm_resp.status_code == 409
    assert confirm_resp.json()["error"]["code"] == "ASSET_OBJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_confirm_upload_and_download_flow(async_client: AsyncClient):
    """Verify successful object confirmation and signed download generation against MinIO."""
    token, ws_id = await _setup_user_workspace(async_client, "Real Uploader")
    headers = {"Authorization": f"Bearer {token}"}

    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers=headers,
        json={
            "original_filename": "logo.svg",
            "mime_type": "image/svg+xml",
            "asset_type": "image",
        },
    )
    asset_id = intent_resp.json()["asset_id"]
    storage_key = intent_resp.json()["storage_key"]

    # Simulate client upload by putting small dummy payload directly to MinIO
    storage = get_storage_provider()
    payload = b"<svg><circle r='10'/></svg>"
    storage.s3_client.put_object(
        Bucket=storage.bucket_name,
        Key=storage_key,
        Body=payload,
        ContentType="image/svg+xml",
    )

    try:
        # Confirm upload
        confirm_resp = await async_client.post(
            f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/confirm",
            headers=headers,
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "ready"
        assert confirm_resp.json()["size_bytes"] == len(payload)

        # Generate signed download URL
        dl_resp = await async_client.get(
            f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/download",
            headers=headers,
        )
        assert dl_resp.status_code == 200
        assert "download_url" in dl_resp.json()
        assert storage_key in dl_resp.json()["download_url"]
    finally:
        storage.delete_object(storage_key)


@pytest.mark.asyncio
async def test_cross_workspace_asset_isolation(async_client: AsyncClient):
    """Verify User B cannot view or download User A's asset."""
    token_a, ws_id_a = await _setup_user_workspace(async_client, "Asset Owner")
    token_b, ws_id_b = await _setup_user_workspace(async_client, "Asset Intruder")

    # User A creates upload intent
    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id_a}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"original_filename": "confidential_brief.pdf", "mime_type": "application/pdf"},
    )
    asset_a_id = intent_resp.json()["asset_id"]

    # User B attempts to access User A's asset inside User B's workspace URL -> 404
    cross_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id_b}/assets/{asset_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_resp.status_code == 404
    assert cross_resp.json()["error"]["code"] == "ASSET_NOT_FOUND"

    # User B attempts to access User A's workspace directly -> 403 Forbidden
    forbidden_resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id_a}/assets/{asset_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["error"]["code"] == "WORKSPACE_FORBIDDEN"


@pytest.mark.asyncio
async def test_soft_delete_asset(async_client: AsyncClient):
    """Verify soft-deleted asset is excluded from list and get."""
    token, ws_id = await _setup_user_workspace(async_client, "Asset Deleter")
    headers = {"Authorization": f"Bearer {token}"}

    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers=headers,
        json={"original_filename": "scratch.wav", "mime_type": "audio/wav"},
    )
    asset_id = intent_resp.json()["asset_id"]

    # Soft-delete asset
    del_resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204

    # Excluded from list
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0

    # Get returns 404
    get_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets/{asset_id}", headers=headers)
    assert get_resp.status_code == 404
