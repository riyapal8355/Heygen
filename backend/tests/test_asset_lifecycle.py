"""Integration and rollback safety tests for AssetLifecycleManager and direct storage operations."""

import hashlib
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.media.temp_manager import MediaTempManager
from app.repositories.asset import AssetRepository
from app.services.asset_lifecycle import AssetLifecycleManager
from app.storage.s3 import get_storage_provider


async def _create_test_workspace_user(async_client: AsyncClient, name: str) -> tuple[uuid.UUID, uuid.UUID]:
    email = f"lifecycle_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    user_id = uuid.UUID(data["user"]["id"])
    token = data["tokens"]["access_token"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    ws_id = uuid.UUID(ws_resp.json()[0]["id"])
    return ws_id, user_id


def test_storage_direct_bytes_and_file_io():
    """Verify S3StorageProvider direct upload_bytes, get_object_bytes, upload_file, and download_file."""
    storage = get_storage_provider()
    test_key = f"tests/direct_io_{uuid.uuid4().hex[:8]}.bin"
    payload = b"Direct storage byte transfer test payload \x00\x01\x02\xFF"

    try:
        # 1. upload_bytes & get_object_bytes
        storage.upload_bytes(payload, test_key, content_type="application/octet-stream")
        assert storage.object_exists(test_key) is True

        downloaded = storage.get_object_bytes(test_key)
        assert downloaded == payload

        # 2. upload_file & download_file
        with MediaTempManager() as temp_dir:
            local_src = temp_dir / "src.bin"
            local_src.write_bytes(payload * 2)

            file_key = f"tests/file_io_{uuid.uuid4().hex[:8]}.bin"
            storage.upload_file(str(local_src), file_key, content_type="application/octet-stream")
            assert storage.object_exists(file_key) is True

            local_dst = temp_dir / "dst.bin"
            storage.download_file(file_key, str(local_dst))
            assert local_dst.read_bytes() == payload * 2

            storage.delete_object(file_key)
            assert storage.object_exists(file_key) is False

    finally:
        storage.delete_object(test_key)
        assert storage.object_exists(test_key) is False


@pytest.mark.asyncio
async def test_asset_lifecycle_ingest_bytes(async_client: AsyncClient):
    """Verify AssetLifecycleManager uploads bytes, calculates sha256, and creates ready Asset record."""
    ws_id, user_id = await _create_test_workspace_user(async_client, "Lifecycle Bytes")
    storage = get_storage_provider()

    raw_wav_bytes = b"RIFF....WAVEfmt ....data...."
    expected_sha = hashlib.sha256(raw_wav_bytes).hexdigest()

    async with async_session_factory() as db:
        manager = AssetLifecycleManager(db=db, storage=storage)
        asset = await manager.ingest_generated_asset(
            workspace_id=ws_id,
            created_by=user_id,
            content=raw_wav_bytes,
            original_filename="synth_audio.wav",
            asset_type="audio",
            mime_type="audio/wav",
            metadata={"sample_rate": 24000, "duration": 3.5},
        )
        assert asset is not None
        assert asset.workspace_id == ws_id
        assert asset.created_by == user_id
        assert asset.status == "ready"
        assert asset.asset_type == "audio"
        assert asset.mime_type == "audio/wav"
        assert asset.checksum_sha256 == expected_sha
        assert asset.size_bytes == len(raw_wav_bytes)
        assert asset.extra_metadata["sha256"] == expected_sha
        assert asset.extra_metadata["generated"] is True

        # Verify object exists in storage and is retrievable
        assert storage.object_exists(asset.storage_key) is True
        retrieved_bytes = storage.get_object_bytes(asset.storage_key)
        assert retrieved_bytes == raw_wav_bytes

        # Cleanup storage object
        storage.delete_object(asset.storage_key)


@pytest.mark.asyncio
async def test_asset_lifecycle_ingest_file(async_client: AsyncClient):
    """Verify AssetLifecycleManager handles Path inputs, computes file hash, and stores asset."""
    ws_id, user_id = await _create_test_workspace_user(async_client, "Lifecycle File")
    storage = get_storage_provider()

    with MediaTempManager() as temp_dir:
        video_file = temp_dir / "render.mp4"
        file_content = b"\x00\x00\x00\x18ftypmp42fake-video-bytes"
        video_file.write_bytes(file_content)
        expected_sha = hashlib.sha256(file_content).hexdigest()

        async with async_session_factory() as db:
            manager = AssetLifecycleManager(db=db, storage=storage)
            asset = await manager.ingest_generated_asset(
                workspace_id=ws_id,
                created_by=user_id,
                content=video_file,
                original_filename="render.mp4",
                asset_type="video",
                mime_type="video/mp4",
                metadata={"resolution": "1920x1080"},
            )

            assert asset.status == "ready"
            assert asset.checksum_sha256 == expected_sha
            assert asset.size_bytes == len(file_content)
            assert storage.object_exists(asset.storage_key) is True

            storage.delete_object(asset.storage_key)


@pytest.mark.asyncio
async def test_asset_lifecycle_rollback_on_db_failure(async_client: AsyncClient):
    """Verify that if DB persistence fails after storage upload, the uploaded object is cleaned up."""
    ws_id, user_id = await _create_test_workspace_user(async_client, "Rollback Tester")
    storage = get_storage_provider()
    payload = b"Temporary data that should not become an orphan in storage"

    deleted_keys = []
    original_delete = storage.delete_object

    def track_delete(key: str) -> bool:
        deleted_keys.append(key)
        return original_delete(key)

    storage.delete_object = track_delete

    try:
        async with async_session_factory() as db:
            manager = AssetLifecycleManager(db=db, storage=storage)

            # Mock asset_repo.create to simulate a database crash
            with patch.object(
                manager.asset_repo,
                "create",
                side_effect=RuntimeError("Simulated PostgreSQL connection failure during asset insert"),
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    await manager.ingest_generated_asset(
                        workspace_id=ws_id,
                        created_by=user_id,
                        content=payload,
                        original_filename="will_fail.wav",
                        asset_type="audio",
                        mime_type="audio/wav",
                    )
                assert "PostgreSQL connection failure" in str(exc_info.value)

            # Verify rollback: delete_object was called for the uploaded object
            assert len(deleted_keys) == 1
            orphaned_key = deleted_keys[0]
            assert storage.object_exists(orphaned_key) is False

    finally:
        storage.delete_object = original_delete
