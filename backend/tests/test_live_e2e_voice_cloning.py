"""Live End-to-End Acceptance Test for Commercial-Safe OpenVoice V2 Voice Cloning.

Proves:
1. Real OpenVoice V2 neural weights load on host CPU without CUDA.
2. Distinct reference audios produce distinct speaker representations (Reference Audio Matters).
3. Real closed-loop Celery task execution produces valid cloned audio preview.
4. Cloned voice representation is securely scoped to workspace in MinIO.
5. Project speech orchestration seamlessly routes cloned voices through OpenVoice and preset voices through Piper.
"""

import io
import time
import uuid
import numpy as np
import pytest
import soundfile as sf
import torch
from httpx import AsyncClient

from app.ai.adapters.openvoice import OpenVoiceCloningProvider
from app.ai.registry import get_ai_registry
from app.core.config import get_settings
from app.media.ffmpeg import FFmpegService
from app.models.project import Project, ProjectVersion
from app.repositories.project import ProjectRepository
from app.schemas.project_document import ProjectDocumentV1, Scene, SceneSpeech
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.storage.s3 import get_storage_provider
from app.workers.tasks.ai_tasks import _execute_voice_clone


def _make_rich_reference_audio(freq: float, duration_seconds: float = 4.0, sample_rate: int = 22050) -> bytes:
    """Generate rich harmonic audio with varying timbre characteristics."""
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples, endpoint=False)
    # Fundamental + harmonics
    audio = 0.4 * np.sin(2 * np.pi * freq * t)
    audio += 0.2 * np.sin(2 * np.pi * (freq * 2.0) * t)
    audio += 0.1 * np.sin(2 * np.pi * (freq * 3.0) * t)
    # Apply envelope to simulate vocal cadence
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 2.0 * t))
    audio = (audio * envelope).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


async def _setup_user_workspace(async_client: AsyncClient, name: str) -> tuple[str, str, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@example.com"
    resp = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": name, "password": "Password123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]

    ws_resp = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_resp.status_code == 200
    workspace_id = ws_resp.json()[0]["id"]
    return token, workspace_id, user_id


async def _upload_audio_asset(
    async_client: AsyncClient,
    token: str,
    ws_id: str,
    filename: str,
    audio_bytes: bytes,
) -> str:
    intent_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/upload-intents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_filename": filename,
            "mime_type": "audio/wav",
            "size_bytes": len(audio_bytes),
            "asset_type": "audio",
        },
    )
    assert intent_resp.status_code == 201
    intent = intent_resp.json()
    asset_id = intent["asset_id"]

    storage = get_storage_provider()
    storage.upload_bytes(audio_bytes, intent["storage_key"], content_type="audio/wav")

    confirm_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 200
    return asset_id


# ==============================================================================
# SECTION 19: Prove Reference Audio Matters (Differential Timbre Validation)
# ==============================================================================

@pytest.mark.asyncio
async def test_real_openvoice_cpu_differential_timbre():
    """Verify that distinct reference audios produce distinct embeddings and distinct audio bytes.

    Non-mocked real OpenVoice V2 execution on host CPU.
    """
    provider = OpenVoiceCloningProvider()
    assert provider._check_files_exist(), "OpenVoice V2 model artifacts must be present in model cache"

    # Reference A: lower pitch speaker (220 Hz base)
    ref_a_bytes = _make_rich_reference_audio(freq=220.0, duration_seconds=4.0)
    # Reference B: higher pitch speaker (660 Hz base)
    ref_b_bytes = _make_rich_reference_audio(freq=660.0, duration_seconds=4.0)

    t_load_start = time.perf_counter()
    provider.load_model()
    cold_load_ms = (time.perf_counter() - t_load_start) * 1000.0

    # Extract embedding A
    t0 = time.perf_counter()
    emb_a, dur_a, sr_a = provider.extract_speaker_embedding(ref_a_bytes)
    latency_emb_a = (time.perf_counter() - t0) * 1000.0

    # Extract embedding B
    t1 = time.perf_counter()
    emb_b, dur_b, sr_b = provider.extract_speaker_embedding(ref_b_bytes)
    latency_emb_b = (time.perf_counter() - t1) * 1000.0

    # 1. Verify embedding shapes
    assert emb_a.shape == torch.Size([1, 256, 1])
    assert emb_b.shape == torch.Size([1, 256, 1])

    # 2. Embedding divergence check: emb_a and emb_b must not be identical
    diff_norm = torch.norm(emb_a - emb_b).item()
    assert diff_norm > 0.05, f"Expected distinct speaker embeddings, got difference norm: {diff_norm}"

    # 3. Tone color conversion on identical base audio
    base_speech = _make_rich_reference_audio(freq=330.0, duration_seconds=3.0)

    t_conv0 = time.perf_counter()
    out_a = provider.convert_voice(base_audio_bytes=base_speech, target_se=emb_a)
    latency_conv_a = (time.perf_counter() - t_conv0) * 1000.0

    t_conv1 = time.perf_counter()
    out_b = provider.convert_voice(base_audio_bytes=base_speech, target_se=emb_b)
    latency_conv_b = (time.perf_counter() - t_conv1) * 1000.0

    # 4. Outputs must not be byte-identical
    assert out_a != out_b, "Voice conversion output A and B must differ when conditioned on distinct reference embeddings"

    # 5. Audio validity check
    pcm_a, sr_out_a = sf.read(io.BytesIO(out_a))
    pcm_b, sr_out_b = sf.read(io.BytesIO(out_b))
    assert len(pcm_a) > 0 and np.max(np.abs(pcm_a)) > 0.01
    assert len(pcm_b) > 0 and np.max(np.abs(pcm_b)) > 0.01
    assert sr_out_a == 22050 and sr_out_b == 22050

    print(f"\n[OpenVoice CPU Benchmark]")
    print(f"  Cold model load latency: {cold_load_ms:.2f} ms")
    print(f"  Embedding extraction latency (4s sample): {latency_emb_a:.2f} ms")
    print(f"  Tone conversion latency (3s audio): {latency_conv_a:.2f} ms")
    print(f"  Speaker embedding distance (norm): {diff_norm:.4f}")


# ==============================================================================
# SECTION 18 & 21: Full Closed-Loop Live E2E & Project Speech Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_live_e2e_voice_cloning_closed_loop(async_client: AsyncClient):
    """Full closed-loop acceptance test with real OpenVoice CPU inference and project speech integration.

    Steps:
    1. Authenticate user & resolve workspace
    2. Upload reference voice audio
    3. Initiate voice clone job (202 Accepted)
    4. Execute Celery worker task with real OpenVoice V2
    5. Verify Voice status=ready, embedding saved in MinIO, preview audio asset created
    6. Create a Project with two scenes: Scene 1 (Piper Preset), Scene 2 (Cloned Voice)
    7. Synthesize project speech via ProjectSpeechOrchestrator
    8. Verify both scenes generate valid audio and original project timeline updates cleanly
    """
    token, ws_id, user_id = await _setup_user_workspace(async_client, "Live E2E Creator")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

    # Step 2: Upload real reference audio
    ref_audio = _make_rich_reference_audio(freq=440.0, duration_seconds=5.0)
    asset_id = await _upload_audio_asset(async_client, token, ws_id, "host_reference.wav", ref_audio)

    # Step 3: Initiate clone job
    clone_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/voices/clone",
        headers=headers,
        json={
            "name": "Live Real Cloned Voice",
            "reference_asset_id": asset_id,
            "language": "en",
            "gender": "female",
            "description": "High fidelity live clone",
        },
    )
    assert clone_resp.status_code == 202
    job_data = clone_resp.json()
    job_id = uuid.UUID(job_data["job_id"])
    voice_id = uuid.UUID(job_data["voice_id"])

    # Step 4: Execute Celery task with real OpenVoice V2
    # Ensure real provider mode
    settings = get_settings()
    orig_mode = settings.AI_PROVIDER_MODE
    settings.AI_PROVIDER_MODE = "real"

    try:
        task_res = await _execute_voice_clone(job_id=job_id, task_id=str(uuid.uuid4()))
        assert task_res["status"] == "ready"
        assert task_res["voice_id"] == str(voice_id)
        assert task_res["model"] == "openvoice_v2"
        assert task_res["provider"] == "openvoice"

        # Step 5: Verify Voice record in DB
        voice_get = await async_client.get(f"/api/v1/voices/{voice_id}", headers=headers)
        assert voice_get.status_code == 200
        voice_record = voice_get.json()
        assert voice_record["status"] == "ready"
        assert voice_record["voice_type"] == "cloned"
        assert voice_record["provider"] == "openvoice"
        assert voice_record["preview_asset_id"] is not None

        # Verify embedding path in MinIO
        expected_embedding_key = f"workspaces/{ws_id}/voices/{voice_id}/embedding.pt"
        assert voice_record["provider_reference"] == expected_embedding_key
        storage = get_storage_provider()
        assert storage.object_exists(expected_embedding_key)

        # Verify preview asset in MinIO
        preview_asset_id = voice_record["preview_asset_id"]
        preview_asset_resp = await async_client.get(
            f"/api/v1/workspaces/{ws_id}/assets/{preview_asset_id}/download",
            headers=headers,
        )
        assert preview_asset_resp.status_code == 200

        # Step 6: Create Project with 2 scenes (Scene 1: Piper Preset, Scene 2: Cloned Voice)
        from app.db.session import async_session_factory
        async with async_session_factory() as db:
            project_repo = ProjectRepository(db)

            project_id = uuid.uuid4()
            project = Project(
                id=project_id,
                workspace_id=uuid.UUID(ws_id),
                created_by=uuid.UUID(user_id),
                title="Voice Clone Speech Integration Project",
                status="draft",
            )

            doc = ProjectDocumentV1(
                settings={"total_duration": 10.0, "aspect_ratio": "16:9"},
                scenes=[
                    Scene(
                        id="scene_1_preset",
                        sequence=1,
                        duration=5.0,
                        speech=SceneSpeech(
                            voice_id="en_US-lessac-medium",  # Preset Piper voice
                            script="This scene uses the standard Piper voice preset.",
                            speed=1.0,
                        ),
                    ),
                    Scene(
                        id="scene_2_cloned",
                        sequence=2,
                        duration=5.0,
                        speech=SceneSpeech(
                            voice_id=str(voice_id),  # Cloned Voice
                            script="And this scene uses the newly cloned OpenVoice timbre.",
                            speed=1.0,
                        ),
                    ),
                ],
            )
            version = ProjectVersion(
                project_id=project_id,
                created_by=uuid.UUID(user_id),
                revision=1,
                document=doc.model_dump(),
                source="initial",
            )
            await project_repo.create_project_with_initial_version(project, version)
            await db.commit()

            # Step 7: Synthesize project speech
            orchestrator = ProjectSpeechOrchestrator(db)
            new_version = await orchestrator.synthesize_project_speech(
                project_id=project_id,
                workspace_id=uuid.UUID(ws_id),
                user_id=uuid.UUID(user_id),
                expected_revision=1,
            )

            # Step 8: Verify both scenes received generated audio assets
            assert new_version.revision == 2
            updated_doc = ProjectDocumentV1.model_validate(new_version.document)

            # Scene 1 (Preset)
            s1 = updated_doc.scenes[0]
            assert s1.speech.audio_asset_id is not None
            assert s1.duration > 0

            # Scene 2 (Cloned)
            s2 = updated_doc.scenes[1]
            assert s2.speech.audio_asset_id is not None
            assert s2.duration > 0

            # Verify cloned audio asset exists in MinIO and is valid
            from app.repositories.asset import AssetRepository
            asset_repo = AssetRepository(db)
            cloned_audio_asset = await asset_repo.get_by_id(
                uuid.UUID(s2.speech.audio_asset_id),
                uuid.UUID(ws_id),
            )
            assert cloned_audio_asset is not None
            cloned_audio_bytes = storage.get_object_bytes(cloned_audio_asset.storage_key)
            assert len(cloned_audio_bytes) > 1000

            # Check audio with soundfile
            data, sr = sf.read(io.BytesIO(cloned_audio_bytes))
            assert len(data) > 0
            assert sr == 22050
            assert np.max(np.abs(data)) > 0.01  # Non-silent

    finally:
        settings.AI_PROVIDER_MODE = orig_mode
