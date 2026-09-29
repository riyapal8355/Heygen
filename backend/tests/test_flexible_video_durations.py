"""Comprehensive test suite verifying flexible video durations in HeyZen.

Tests verify:
1. Duration scaling across 15s, 30s, 60s, 2 min (120s), 5 min (300s), and custom longer durations (600s, 900s).
2. For every duration:
   - request duration is preserved
   - generated script length scales proportionally
   - scene count scales appropriately (not fixed to 3 scenes)
   - total scene duration matches requested duration (not fixed to ~11s or 30s)
   - ProjectVersion metadata and document settings persist planned duration and scene durations
   - API /projects/generate accepts and processes custom durations
"""

import pytest
import uuid
from httpx import AsyncClient

from app.core.config import get_settings
from app.db.seeds import AVATAR_ANNIE_ID
from app.models.project import Project, ProjectVersion
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import ProjectDocumentV1
from app.services.video_agent_service import VideoAgentService
from app.ai.adapters.mock import MockLLMProvider


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target_seconds, expected_min_scenes, expected_min_words",
    [
        (15.0, 2, 25),      # 15 sec -> 2 scenes, >= 25 words
        (30.0, 3, 50),      # 30 sec -> 3 scenes, >= 50 words
        (60.0, 4, 100),     # 60 sec -> 4 scenes, >= 100 words
        (120.0, 8, 200),    # 2 min (120s) -> 8 scenes, >= 200 words
        (300.0, 15, 500),   # 5 min (300s) -> 15 scenes, >= 500 words
        (600.0, 25, 1000),  # 10 min (600s) -> >= 25 scenes, >= 1000 words
    ],
)
async def test_video_agent_scales_with_duration(
    db_session,
    test_user,
    test_workspace,
    target_seconds,
    expected_min_scenes,
    expected_min_words,
):
    """Verify script length, scene count, and total duration scale with requested duration."""
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Explain modern enterprise generative AI video creation workflows",
        target_duration_seconds=target_seconds,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_ANNIE_ID),
        voice_id="voice_mock_en_marcus",
        video_tone="Professional",
        auto_synthesize_speech=False,
    )

    project, initial_version, job_id = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    assert project.id is not None
    assert project.status == "draft"

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    scene_count = len(doc.scenes)
    total_scene_duration = round(sum(s.duration for s in doc.scenes), 2)
    full_script = " ".join((s.speech.script if s.speech else "") for s in doc.scenes)
    total_words = len(full_script.split())

    # 1. No fixed 3-scene behavior for non-30s durations
    assert scene_count >= expected_min_scenes, (
        f"For target {target_seconds}s, expected at least {expected_min_scenes} scenes, got {scene_count}"
    )

    # 2. Total scene duration must match requested duration (not fixed ~11s or 30s)
    assert abs(total_scene_duration - target_seconds) <= 0.5, (
        f"For target {target_seconds}s, total scene duration was {total_scene_duration}s"
    )

    # 3. Document settings total_duration matches
    assert abs(doc.settings.total_duration - target_seconds) <= 0.5

    # 4. Project duration_ms matches
    assert abs(project.duration_ms - int(target_seconds * 1000)) <= 500

    # 5. Script length scales with duration
    assert total_words >= expected_min_words, (
        f"For target {target_seconds}s, expected at least {expected_min_words} words, got {total_words}"
    )

    # 6. Requirement 7: Persisted in metadata
    meta = doc.metadata
    assert meta["target_duration_seconds"] == target_seconds
    assert meta["requested_duration_seconds"] == target_seconds
    assert abs(meta["actual_planned_duration_seconds"] - target_seconds) <= 0.5
    assert meta["scene_count"] == scene_count
    assert len(meta["scene_durations"]) == scene_count
    assert abs(sum(meta["scene_durations"]) - target_seconds) <= 0.5


@pytest.mark.asyncio
async def test_custom_longer_duration_generation(db_session, test_user, test_workspace):
    """Verify custom duration like 420 seconds (7 minutes) is accepted and scales correctly."""
    custom_seconds = 420.0
    service = VideoAgentService(db_session)
    req = GenerateProjectRequest(
        prompt="Comprehensive masterclass on video editing and AI avatar technology",
        target_duration_seconds=custom_seconds,
        aspect_ratio="16:9",
        avatar_id=str(AVATAR_ANNIE_ID),
        voice_id="voice_mock_en_marcus",
        video_tone="Educational",
        auto_synthesize_speech=False,
    )

    project, initial_version, _ = await service.generate_project(
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        request=req,
    )

    doc = ProjectDocumentV1.model_validate(initial_version.document)
    scene_count = len(doc.scenes)
    total_scene_duration = round(sum(s.duration for s in doc.scenes), 2)

    # Must NOT be clamped to 30 or 300 seconds
    assert scene_count >= 15
    assert abs(total_scene_duration - custom_seconds) <= 0.5
    assert doc.metadata["target_duration_seconds"] == custom_seconds
    assert doc.metadata["requested_duration_seconds"] == custom_seconds
    assert abs(doc.metadata["actual_planned_duration_seconds"] - custom_seconds) <= 0.5


@pytest.mark.asyncio
async def test_duration_progression_strictly_increases():
    """Verify that longer durations produce strictly longer scripts and more scenes."""
    provider = MockLLMProvider()
    durations = [15.0, 30.0, 60.0, 120.0, 300.0, 600.0]
    results = []

    for dur in durations:
        res = await provider.generate_script(
            prompt="Scaling AI video technology across global teams",
            context={"target_duration_seconds": dur},
        )
        scene_count = len(res.suggested_scenes)
        total_dur = sum(s["duration"] for s in res.suggested_scenes)
        word_count = len(res.script.split())
        results.append((dur, scene_count, total_dur, word_count))

    for i in range(len(results) - 1):
        dur_a, scenes_a, total_a, words_a = results[i]
        dur_b, scenes_b, total_b, words_b = results[i + 1]

        assert dur_b > dur_a
        assert scenes_b >= scenes_a, f"Scenes did not scale: {scenes_a} -> {scenes_b}"
        assert words_b > words_a, f"Words did not scale: {words_a} -> {words_b}"
        assert abs(total_a - dur_a) <= 0.1
        assert abs(total_b - dur_b) <= 0.1


@pytest.mark.asyncio
async def test_api_generate_project_accepts_custom_duration(async_client: AsyncClient, test_user, test_workspace):
    """Verify POST /projects/generate respects custom duration and does not clamp to 30s."""
    unique_email = f"duration_test_{uuid.uuid4().hex[:8]}@example.com"
    res_signup = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": unique_email, "password": "Password123!", "display_name": "Duration Test"},
    )
    assert res_signup.status_code == 201
    auth_data = res_signup.json()
    token = auth_data["tokens"]["access_token"]
    ws_id = auth_data["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    custom_dur = 180.0  # 3 minutes
    res = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects/generate",
        headers=headers,
        json={
            "prompt": "Full company showcase and product roadmap review",
            "target_duration_seconds": custom_dur,
            "run_async": False,
            "auto_synthesize_speech": False,
        },
    )
    assert res.status_code in (200, 201), f"Generate failed: {res.text}"
    project_data = res.json()

    # Project duration_ms must match ~180,000 ms, not 30,000 ms or 11,000 ms
    assert abs(project_data["duration_ms"] - int(custom_dur * 1000)) <= 1000

    # Fetch latest version to verify document settings & metadata
    ver_res = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/projects/{project_data['id']}/versions/latest",
        headers=headers,
    )
    assert ver_res.status_code == 200
    ver_data = ver_res.json()
    doc = ver_data["document"]

    assert abs(doc["settings"]["total_duration"] - custom_dur) <= 0.5
    assert doc["metadata"]["requested_duration_seconds"] == custom_dur
    assert doc["metadata"]["target_duration_seconds"] == custom_dur
    assert abs(doc["metadata"]["actual_planned_duration_seconds"] - custom_dur) <= 0.5
    assert len(doc["scenes"]) >= 8  # 180s -> 8+ scenes, NOT 3 scenes!
