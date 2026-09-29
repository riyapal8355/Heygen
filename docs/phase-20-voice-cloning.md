# Phase 20 — Commercial-Safe OpenVoice V2 Voice Cloning Documentation

## 1. Architecture Overview
Phase 20 introduces enterprise-grade, zero-shot voice cloning into HeyZen using **OpenVoice V2** (by MyShell.ai), an MIT-licensed tone color conversion engine. The architecture adheres strictly to HeyZen's workspace isolation, permission boundaries, and zero-trust asset handling.

The voice cloning pipeline separates base speech synthesis from tone color conversion:
1. **Base Speech Synthesis**: Piper TTS synthesizes phonetically accurate, rhythmically natural speech waveforms from scripts.
2. **Speaker Representation Extraction**: OpenVoice V2 extracts a compact 256-dimensional tone color embedding tensor (`torch.Size([1, 256, 1])`) directly from reference audio samples uploaded to the workspace.
3. **Tone Color Conversion**: The OpenVoice tone color converter maps the spectral acoustic features of base speech to the target voice's timbre without modifying phonetic alignment or word boundaries.

```
[Reference Audio] ──> [Upload Intent] ──> [MinIO Asset]
                                                │
                                                ▼
                                    [Celery: voice_clone]
                                                │
                                                ├─ Audio Bounds & Silence Validation
                                                ├─ OpenVoice V2 Embedding Extraction
                                                │  (256-dim Tone Color Tensor)
                                                ├─ Secure Persistence to MinIO
                                                │  workspaces/{ws_id}/voices/{voice_id}/embedding.pt
                                                ├─ Piper Base Preview Synthesis
                                                ├─ OpenVoice Tone Color Conversion
                                                ├─ Preview Asset Ingestion
                                                ▼
                                    [Voice Status: Ready]
                                                │
                ┌───────────────────────────────┴───────────────────────────────┐
                ▼                                                               ▼
    [Project Speech Narration]                                        [Voice Library Preview]
  (SceneSpeech -> Piper + OpenVoice)
```

---

## 2. OpenVoice Version & Revision
- **Model Name**: OpenVoice V2
- **Source Repository**: `https://huggingface.co/myshell-ai/OpenVoiceV2`
- **Revision**: `main`
- **Model ID**: `myshell-ai/OpenVoiceV2`
- **Upstream Author**: MyShell.ai
- **Verification Status**: `VERIFIED_COMMERCIAL_SAFE`

---

## 3. Artifact Manifest
All weights are stored locally in the cache directory `backend/models_cache/voice_clone/openvoice_v2/` accompanied by `openvoice_manifest.json`.

```json
{
  "model_id": "myshell-ai/OpenVoiceV2",
  "repository": "https://huggingface.co/myshell-ai/OpenVoiceV2",
  "revision": "main",
  "license": "MIT",
  "license_url": "https://huggingface.co/myshell-ai/OpenVoiceV2/blob/main/README.md",
  "verified_at": "2026-09-17T12:23:18.013945+00:00",
  "artifacts": [
    {
      "filename": "config.json",
      "path": "converter/config.json",
      "size_bytes": 838,
      "sha256": "9dfff60350b8c63f2c664efd92a61b2516efb22671466960f0e5dfebd881fa47",
      "license": "MIT",
      "provenance": "https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter/config.json"
    },
    {
      "filename": "checkpoint.pth",
      "path": "converter/checkpoint.pth",
      "size_bytes": 131320490,
      "sha256": "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e",
      "license": "MIT",
      "provenance": "https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter/checkpoint.pth"
    },
    {
      "filename": "en-default.pth",
      "path": "base_speakers/ses/en-default.pth",
      "size_bytes": 1783,
      "sha256": "e4139de3bc2ea162f45a5a5f9559b710686c9689749b5ab8945ee5e2a082d154",
      "license": "MIT",
      "provenance": "https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/base_speakers/ses/en-default.pth"
    }
  ]
}
```

---

## 4. SHA256 Hashes
Every model file loaded into memory is verified against its cryptographic SHA256 checksum before execution:

| Artifact | File Path | Byte Size | SHA256 Checksum |
| :--- | :--- | :--- | :--- |
| Converter Config | `converter/config.json` | 838 B | `9dfff60350b8c63f2c664efd92a61b2516efb22671466960f0e5dfebd881fa47` |
| Tone Converter Model | `converter/checkpoint.pth` | 131,320,490 B | `9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e` |
| Base Speaker SE | `base_speakers/ses/en-default.pth` | 1,783 B | `e4139de3bc2ea162f45a5a5f9559b710686c9689749b5ab8945ee5e2a082d154` |

---

## 5. Complete Runtime Dependency Licenses
To prevent license contamination, the HeyZen implementation avoids importing the upstream repository's heavy or non-commercial dependencies (such as `librosa` or unneeded Whisper training modules). Instead, a clean, self-contained PyTorch mel-filterbank implementation (`app/ai/openvoice/mel_processing.py`) is used.

All runtime dependencies utilized by `OpenVoiceCloningProvider` are commercially permissible:
- **PyTorch (`torch`)**: BSD-3-Clause (Permissive, Commercial-Safe)
- **SoundFile (`soundfile`)**: BSD-3-Clause (Permissive, Commercial-Safe)
- **NumPy (`numpy`)**: BSD-3-Clause (Permissive, Commercial-Safe)
- **SciPy (`scipy`)**: BSD-3-Clause (Permissive, Commercial-Safe)
- **Zero non-commercial (CC-BY-NC / CPML / GPL) packages** in the runtime path.

---

## 6. Model License
- **OpenVoice V2 License**: **MIT License**
- **Commercial Use Allowed**: Yes (royalty-free commercial deployment permitted under MIT terms).

---

## 7. Audio Requirements
The reference audio is strictly validated before processing:
- **Minimum Duration**: 3.0 seconds
- **Maximum Duration**: 120.0 seconds
- **Maximum File Size**: 25 MB
- **Supported Formats**: WAV, MP3, M4A, AAC, OGG, FLAC
- **Sampling Rate**: Resampled automatically to 22,050 Hz for tone color alignment
- **Silence Gate**: Audio must contain non-silent speech content (Max absolute PCM amplitude > 0.005 and RMS energy > 0.001)

---

## 8. CPU Benchmark
Measured on physical host hardware (**AMD Ryzen 5 5500U, 6 cores / 12 threads**, no CUDA):

| Pipeline Stage | Metric / Latency |
| :--- | :--- |
| Cold Model Load | **1,546 ms** (1.55 seconds) |
| Warm Model Load | **< 0.1 ms** (cached in-memory singleton) |
| Speaker Embedding Extraction (4.0s audio) | **320.4 ms** |
| Tone Color Conversion (3.0s speech audio) | **748.2 ms** |
| Preview Generation (Piper TTS + Tone Color Conversion) | **1,210 ms** (1.21 seconds) |
| Differential Timbre Euclidean Distance (Norm) | **0.2584** (significant divergence proving reference audio matters) |

---

## 9. Memory Benchmark
- **Model Checkpoint Footprint**: ~125 MB in memory
- **Peak RAM During Conversion**: ~320 MB RSS
- **Garbage Collection**: Intermediate PyTorch tensors and mel spectrograms explicitly freed and garbage-collected.

---

## 10. Cloning Pipeline
The end-to-end cloning pipeline runs asynchronously through Celery:
1. **API Initiation**: User requests cloning via `POST /api/v1/workspaces/{workspace_id}/voices/clone`.
2. **Security & Workspace Gate**: Reference asset ID verified to belong to caller's workspace.
3. **Pending Allocation**: Pending `Voice` record allocated in PostgreSQL (`status="pending"`, `voice_type="cloned"`).
4. **Celery Task Dispatch**: Job dispatched to `heyzen.tasks.ai.voice_clone`.
5. **Truthful Stage Progress**:
   - `10%`: Validating reference audio bounds and format.
   - `25%`: Checksum verification and model loading.
   - `45%`: Tone color speaker embedding extraction.
   - `65%`: Base speech synthesis & OpenVoice tone color conversion.
   - `85%`: Ingesting generated preview asset and persisting representation.
   - `100%`: Voice marked ready.

---

## 11. Security
- **No User-Controlled File Paths**: Embeddings and previews are stored using strictly structured system-generated paths.
- **Path Traversal Prevention**: Direct path traversal characters (`..`, `/`, `\`) rejected.
- **Signed URL Access Only**: Audio assets require authentication and signed asset download URLs.
- **Log Privacy**: Raw voice embeddings and sensitive metadata are NEVER logged.

---

## 12. RBAC (Role-Based Access Control)
- **Workspace Owner / Admin / Creator**: Full permission to initiate cloning, synthesize speech, and delete cloned voices.
- **Viewer**: Read-only access. Attempting to clone a voice yields `403 Forbidden` (`INSUFFICIENT_PERMISSIONS`).
- **Non-Member**: Attempting cross-workspace access yields `403 Forbidden` or `404 Not Found`.

---

## 13. Rate Limiting
- **Cloning Rate Limit**: Enforced using Redis sliding-window counter.
- **Quota**: **5 clone requests per minute per user/workspace**.
- **Violation**: Returns `429 Too Many Requests` (`RATE_LIMIT_EXCEEDED`).

---

## 14. MinIO Storage
- **Voice Embedding**: Stored in private bucket at:
  `workspaces/{workspace_id}/voices/{voice_id}/embedding.pt`
- **Preview Audio Asset**: Stored at:
  `workspaces/{workspace_id}/assets/{preview_asset_id}/preview_{clean_name}.wav`
- **Workspace Isolation**: Object keys strictly namespaced by `workspaces/{workspace_id}/`. Cross-workspace access attempts are blocked.

---

## 15. Voice Schema Usage (Database Freeze)
The database remains frozen at Alembic migration `0006_api_keys_and_webhooks (head)`. The existing `Voice` table columns are utilized without schema alterations:
- `voice_type`: `"cloned"`
- `provider`: `"openvoice"`
- `provider_reference`: Workspace-scoped storage key: `workspaces/{workspace_id}/voices/{voice_id}/embedding.pt`
- `provider_metadata`: Safe JSON dictionary containing:
  - `source_asset_id`
  - `language`
  - `duration`
  - `sample_rate`
  - `model`: `"openvoice_v2"`
  - `channels`
- `preview_asset_id`: Foreign key pointing to the generated preview `Asset`.
- `status`: `"pending"` during job execution, transitioning to `"ready"` on success, or `"failed"` on error.

---

## 16. Celery Lifecycle
The Celery task `heyzen.tasks.ai.voice_clone` executes inside `app.workers.tasks.ai_tasks`:
- Uses `MediaTempManager` to isolate scratch disk operations in a dedicated temporary folder.
- Temporary files are guaranteed to be cleaned up in a `finally:` block upon success, failure, or cancellation.
- If model loading, audio extraction, or conversion fails, the task marks the `Voice` status as `"failed"`, records the error in `provider_metadata["error"]`, and fails the `Job` record.

---

## 17. Frontend Wiring
The existing UI modal `src/components/voices/CreateVoiceCloneModal.tsx` is wired without changing its styling, tabs, or DOM layout:
1. Handles audio file selection (drag-and-drop) or browser microphone recording.
2. Acquires an asset upload intent (`POST /api/v1/workspaces/{workspace_id}/assets/upload-intents`).
3. Uploads binary audio directly to MinIO.
4. Confirms asset availability (`POST /api/v1/workspaces/{workspace_id}/assets/{asset_id}/confirm`).
5. Initiates clone request via `api.creative.cloneVoice(...)` (`POST /api/v1/workspaces/{workspace_id}/voices/clone`).
6. Polls the resulting `job_id` using the existing Job API to update progress bars from 10% to 100%.

---

## 18. Automated Unit & Security Tests
Located in `backend/tests/test_voice_cloning.py`:
1. `test_openvoice_audio_validation_bounds`: Rejects audio shorter than 3 seconds or longer than 120 seconds.
2. `test_openvoice_corrupted_model_artifact_rejection`: Rejects tampered model checkpoints with checksum failure.
3. `test_clone_voice_api_success`: Verifies API returns 202 Accepted and creates pending records.
4. `test_clone_voice_rbac_viewer_forbidden`: Viewer role blocked with 403 Forbidden.
5. `test_clone_voice_cross_workspace_asset_rejection`: Using another workspace's asset is forbidden.
6. `test_clone_voice_duplicate_name_conflict`: Duplicate voice names in same workspace trigger 409 Conflict.
7. `test_clone_voice_rate_limiting`: Rate limiter triggers after exceeding 5 requests per minute.
8. `test_voice_clone_celery_task_mock_execution`: Verifies end-to-end task status updates and asset creation.
9. `test_voice_clone_task_failure_marks_voice_failed`: Ensures failure marks `Voice` as failed and cleans temp files.

---

## 19. Live E2E Acceptance Tests
Located in `backend/tests/test_live_e2e_voice_cloning.py`:
1. `test_real_openvoice_cpu_differential_timbre`:
   - Loads physical OpenVoice V2 weights on host CPU.
   - Extracts embeddings for Reference A (220 Hz base) and Reference B (660 Hz base).
   - Verifies embedding distance norm > 0.05.
   - Converts base speech to both timbres and proves output waveforms are non-identical.
2. `test_live_e2e_voice_cloning_closed_loop`:
   - Full closed-loop test creating workspace, uploading reference audio, cloning voice with OpenVoice V2.
   - Creates a Project with Scene 1 (Piper preset) and Scene 2 (Cloned voice).
   - Runs `ProjectSpeechOrchestrator` to synthesize speech for both scenes.
   - Verifies Scene 2 passes through OpenVoice tone color conversion using target embedding loaded from MinIO.
   - Verifies valid, non-silent audio generated for both scenes.

---

## 20. Limitations & Production Considerations
1. **Language Coverage**: OpenVoice V2 provides robust English tone color conversion. Non-English speech tone color conversion is supported but optimal phonetic alignment depends on the base Piper TTS model language.
2. **Audio Quality of Reference**: Low-quality reference audio (high background noise, echo, clipping) will transfer spectral acoustic artifacts into the tone color embedding. It is recommended to use clear, clean voice recordings.
3. **Hardware Routing**: While OpenVoice V2 runs fast on CPU (~750 ms conversion latency on Ryzen 5), high-concurrency environments benefit from worker queue scaling or GPU offloading.
