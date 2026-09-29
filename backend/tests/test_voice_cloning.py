"""Comprehensive unit, integration, RBAC, rate-limiting, and error-handling tests

for Phase 20 OpenVoice V2 Voice Cloning.
"""

import io
import json
import uuid
import numpy as np
import pytest
import soundfile as sf
import torch
from httpx import AsyncClient

from app.ai.adapters.openvoice import OpenVoiceCloningProvider
from app.core.exceptions import AIRuntimeUnavailableException, ValidationException
from app.models.workspace import WorkspaceRole
from app.workers.tasks.ai_tasks import _execute_voice_clone


def _generate_test_wav_bytes(duration_seconds: float = 4.0, sample_rate: int = 22050, silent: bool = False) -> bytes:
    """Generate in-memory valid mono WAV audio bytes for testing."""
    num_samples = int(duration_seconds * sample_rate)
    if silent:
        audio = np.zeros(num_samples, dtype=np.float32)
    else:
        # 440 Hz sine wave tone
        t = np.linspace(0, duration_seconds, num_samples, endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


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


async def _create_test_audio_asset(
    async_client: AsyncClient,
    token: str,
    ws_id: str,
    filename: str = "reference.wav",
    content_bytes: bytes = None,
) -> str:
    audio_content = content_bytes or _generate_test_wav_bytes(4.0)
    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_filename": filename,
            "mime_type": "audio/wav",
            "size_bytes": len(audio_content),
            "asset_type": "audio",
        },
    )
    assert intent_resp.status_code == 201
    intent_data = intent_resp.json()
    asset_id = intent_data["asset_id"]

    # Directly upload bytes to storage provider via local backend storage
    from app.storage.s3 import get_storage_provider
    storage = get_storage_provider()
    storage.upload_bytes(audio_content, intent_data["storage_key"], content_type="audio/wav")

    # Confirm asset
    confirm_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 200
    return asset_id


# ==============================================================================
# 1. OpenVoice Provider Unit Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_openvoice_audio_validation_bounds():
    """Verify OpenVoice audio validation bounds: rejects too short, too long, and silent samples."""
    provider = OpenVoiceCloningProvider()

    # 1. Too short (< 3.0 seconds)
    short_audio = _generate_test_wav_bytes(duration_seconds=1.5)
    with pytest.raises(ValidationException) as exc_short:
        provider.extract_speaker_embedding(short_audio)
    assert exc_short.value.code == "VOICE_CLONE_AUDIO_TOO_SHORT"

    # 2. Too long (> 120.0 seconds)
    # Using small sample rate to avoid huge allocation in test
    long_audio = _generate_test_wav_bytes(duration_seconds=125.0, sample_rate=8000)
    with pytest.raises(ValidationException) as exc_long:
        provider.extract_speaker_embedding(long_audio)
    assert exc_long.value.code == "VOICE_CLONE_AUDIO_TOO_LONG"

    # 3. Silent audio
    silent_audio = _generate_test_wav_bytes(duration_seconds=5.0, silent=True)
    with pytest.raises(ValidationException) as exc_silent:
        provider.extract_speaker_embedding(silent_audio)
    assert exc_silent.value.code == "VOICE_CLONE_INVALID_AUDIO"

    # 4. Corrupt non-audio bytes
    with pytest.raises(ValidationException) as exc_corrupt:
        provider.extract_speaker_embedding(b"NOT_A_REAL_WAV_FILE_CONTENT")
    assert exc_corrupt.value.code == "VOICE_CLONE_INVALID_AUDIO"


@pytest.mark.asyncio
async def test_openvoice_corrupted_model_artifact_rejection(tmp_path):
    """Corrupt a model artifact and verify OpenVoice immediately rejects it with VOICE_CLONE_MODEL_UNAVAILABLE."""
    # Create a mock cache directory with a corrupted manifest or file
    mock_model_dir = tmp_path / "corrupt_openvoice"
    mock_model_dir.mkdir(parents=True)
    converter_dir = mock_model_dir / "converter"
    converter_dir.mkdir()
    ses_dir = mock_model_dir / "base_speakers" / "ses"
    ses_dir.mkdir(parents=True)

    # Write corrupt checkpoint
    (converter_dir / "config.json").write_text("{}", encoding="utf-8")
    (converter_dir / "checkpoint.pth").write_bytes(b"CORRUPTED_CHECKPOINT_DATA")
    (ses_dir / "en-default.pth").write_bytes(b"CORRUPTED_SE_DATA")

    # Manifest with specific expected SHA256
    manifest = {
        "model_id": "myshell-ai/OpenVoice-v2",
        "artifacts": [
            {
                "path": "converter/checkpoint.pth",
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "size_bytes": 100,
            }
        ]
    }
    (mock_model_dir / "openvoice_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    corrupt_provider = OpenVoiceCloningProvider(model_dir=mock_model_dir)

    with pytest.raises(AIRuntimeUnavailableException) as exc:
        corrupt_provider.verify_manifest_checksums()
    assert exc.value.code == "VOICE_CLONE_MODEL_UNAVAILABLE"


# ==============================================================================
# 2. API Endpoint & RBAC Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_clone_voice_api_success(async_client: AsyncClient):
    """POST /api/v1/workspaces/{workspace_id}/voices/clone creates pending Voice and 202 Job response."""
    token, ws_id = await _setup_user_workspace(async_client, "Clone Owner")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, token, ws_id, "ref_voice.wav")

    clone_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={
            "name": "Sarah Voice Clone",
            "reference_asset_id": asset_id,
            "language": "en",
            "gender": "female",
            "description": "Studio narrator voice",
        },
    )
    assert clone_resp.status_code == 202
    data = clone_resp.json()
    assert "job_id" in data
    assert "voice_id" in data
    assert data["voice_name"] == "Sarah Voice Clone"
    assert data["status"] == "queued"

    # Verify voice record exists in DB in pending state
    voice_resp = await async_client.get(f"/api/v1/voices/{data['voice_id']}", headers=headers)
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert voice_data["name"] == "Sarah Voice Clone"
    assert voice_data["voice_type"] == "cloned"
    assert voice_data["provider"] == "openvoice"
    assert voice_data["status"] == "pending"


@pytest.mark.asyncio
async def test_clone_voice_rbac_viewer_forbidden(async_client: AsyncClient):
    """Verify Viewer role is forbidden from triggering voice cloning (requires voice.create)."""
    owner_token, ws_id = await _setup_user_workspace(async_client, "Org Owner")
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, owner_token, ws_id, "admin_sample.wav")

    # Invite and create viewer
    viewer_email = f"viewer_{uuid.uuid4().hex[:6]}@example.com"
    signup_resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": viewer_email, "display_name": "Viewer User", "password": "Password123!"},
    )
    viewer_token = signup_resp.json()["tokens"]["access_token"]
    viewer_id = signup_resp.json()["user"]["id"]

    # Add viewer to workspace directly via DB
    from app.db.session import async_session_factory
    from app.models.workspace import WorkspaceMember
    async with async_session_factory() as db:
        member = WorkspaceMember(
            workspace_id=uuid.UUID(ws_id),
            user_id=uuid.UUID(viewer_id),
            role=WorkspaceRole.VIEWER.value,
            status="active",
        )
        db.add(member)
        await db.commit()

    viewer_headers = {"Authorization": f"Bearer {viewer_token}", "X-Workspace-ID": ws_id}

    # Attempt to clone voice as Viewer
    clone_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=viewer_headers,
        json={
            "name": "Unauthorized Clone",
            "reference_asset_id": asset_id,
            "language": "en",
        },
    )
    assert clone_resp.status_code == 403


@pytest.mark.asyncio
async def test_clone_voice_cross_workspace_asset_rejection(async_client: AsyncClient):
    """Attempting to clone a voice in Workspace B using an asset from Workspace A must fail."""
    token_a, ws_a = await _setup_user_workspace(async_client, "Workspace A")
    token_b, ws_b = await _setup_user_workspace(async_client, "Workspace B")

    asset_a = await _create_test_audio_asset(async_client, token_a, ws_a, "asset_a.wav")

    # Attempt to use asset_a in Workspace B
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-ID": ws_b}
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_b}/voices/clone",
        headers=headers_b,
        json={
            "name": "Cross WS Voice",
            "reference_asset_id": asset_a,
            "language": "en",
        },
    )
    assert resp.status_code == 404
    data = resp.json()
    err_code = data.get("error", {}).get("code") or data.get("code")
    assert err_code == "ASSET_NOT_FOUND"


@pytest.mark.asyncio
async def test_clone_voice_duplicate_name_conflict(async_client: AsyncClient):
    """Cloning a voice with an existing name in the same workspace returns 409 VOICE_NAME_EXISTS."""
    token, ws_id = await _setup_user_workspace(async_client, "Conflict Tester")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, token, ws_id, "sample1.wav")

    # First clone
    r1 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={"name": "Unique Voice", "reference_asset_id": asset_id},
    )
    assert r1.status_code == 202

    # Duplicate clone
    r2 = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={"name": "Unique Voice", "reference_asset_id": asset_id},
    )
    assert r2.status_code == 409
    data2 = r2.json()
    err_code2 = data2.get("error", {}).get("code") or data2.get("code")
    assert err_code2 == "VOICE_NAME_EXISTS"


@pytest.mark.asyncio
async def test_clone_voice_rate_limiting(async_client: AsyncClient):
    """Enforcing 5 voice clones per minute: the 6th request receives 429 RATE_LIMIT_EXCEEDED."""
    token, ws_id = await _setup_user_workspace(async_client, "Rate Limit User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, token, ws_id, "ratelimit.wav")

    responses = []
    for i in range(6):
        resp = await async_client.post(
            f"/api/v1/workspaces/{ws_id}/voices/clone",
            headers=headers,
            json={"name": f"Rate Limit Voice {i}", "reference_asset_id": asset_id},
        )
        responses.append(resp)

    # First 5 should succeed (202 Accepted)
    for r in responses[:5]:
        assert r.status_code == 202

    # 6th should be 429
    assert responses[5].status_code == 429
    data6 = responses[5].json()
    err_code6 = data6.get("error", {}).get("code") or data6.get("code")
    assert err_code6 == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# 3. Celery AI Task Execution & Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_voice_clone_celery_task_mock_execution(async_client: AsyncClient):
    """Test full asynchronous Celery task execution with Mock provider."""
    token, ws_id = await _setup_user_workspace(async_client, "Celery Worker User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, token, ws_id, "celery_sample.wav")

    clone_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={"name": "Celery Cloned Voice", "reference_asset_id": asset_id, "language": "en"},
    )
    assert clone_resp.status_code == 202
    job_id = uuid.UUID(clone_resp.json()["job_id"])
    voice_id = uuid.UUID(clone_resp.json()["voice_id"])

    # Directly execute worker task asynchronously
    task_res = await _execute_voice_clone(job_id=job_id, task_id=str(uuid.uuid4()))
    assert task_res["status"] == "ready"
    assert task_res["voice_id"] == str(voice_id)

    # Verify voice status updated to ready
    voice_get = await async_client.get(f"/api/v1/voices/{voice_id}", headers=headers)
    assert voice_get.status_code == 200
    v_data = voice_get.json()
    assert v_data["status"] == "ready"
    assert v_data["provider"] == "openvoice"
    assert v_data["preview_asset_id"] is not None
    assert f"workspaces/{ws_id}/voices/{voice_id}/embedding.pt" in v_data["provider_reference"]

    # Verify embedding was persisted to MinIO
    from app.storage.s3 import get_storage_provider
    storage = get_storage_provider()
    assert storage.object_exists(v_data["provider_reference"])


@pytest.mark.asyncio
async def test_voice_clone_task_failure_marks_voice_failed(async_client: AsyncClient):
    """When source audio asset is missing or corrupt in storage, task fails and Voice is marked failed."""
    token, ws_id = await _setup_user_workspace(async_client, "Failure User")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    asset_id = await _create_test_audio_asset(async_client, token, ws_id, "deleted_source.wav")

    clone_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={"name": "Will Fail Voice", "reference_asset_id": asset_id},
    )
    assert clone_resp.status_code == 202
    job_id = uuid.UUID(clone_resp.json()["job_id"])
    voice_id = uuid.UUID(clone_resp.json()["voice_id"])

    # Delete the asset object in storage to cause an execution failure
    from app.storage.s3 import get_storage_provider
    from app.repositories.asset import AssetRepository
    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        asset_repo = AssetRepository(db)
        asset = await asset_repo.get_by_id(uuid.UUID(asset_id), uuid.UUID(ws_id))
        storage = get_storage_provider()
        storage.delete_object(asset.storage_key)

    # Execute task, expecting failure
    with pytest.raises(Exception):
        await _execute_voice_clone(job_id=job_id, task_id=str(uuid.uuid4()))

    # Verify voice status is marked failed (never left ready)
    voice_get = await async_client.get(f"/api/v1/voices/{voice_id}", headers=headers)
    assert voice_get.status_code == 200
    assert voice_get.json()["status"] == "failed"
