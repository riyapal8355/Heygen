"""Tests verifying exact voice and avatar resolution for Annie and Daniel flows."""

import uuid
import pytest
from sqlalchemy import select

from app.models.avatar import Avatar
from app.models.voice import Voice
from app.models.asset import Asset
from app.storage import get_storage_provider
from app.services.project_speech_service import ProjectSpeechOrchestrator


@pytest.mark.asyncio
async def test_annie_voice_db_record(db_session):
    """Verify Annie voice record exists with piper provider and en_US-lessac-medium reference."""
    stmt = select(Voice).where(Voice.id == uuid.UUID("10000000-0000-0000-0000-000000000003"))
    res = await db_session.execute(stmt)
    voice = res.scalar_one_or_none()

    assert voice is not None, "Annie voice record missing in database"
    assert voice.name == "Annie - Lifelike"
    assert voice.provider == "piper"
    assert voice.provider_reference == "en_US-lessac-medium"
    assert voice.preview_asset_id is not None, "Annie voice preview asset ID missing"

    asset = await db_session.get(Asset, voice.preview_asset_id)
    assert asset is not None, "Annie voice preview Asset record missing"
    assert asset.storage_key.endswith(".wav")


@pytest.mark.asyncio
async def test_annie_avatar_db_record(db_session):
    """Verify Annie avatar record exists and links to real asset in storage."""
    stmt = select(Avatar).where(Avatar.id == uuid.UUID("30000000-0000-0000-0000-000000000002"))
    res = await db_session.execute(stmt)
    avatar = res.scalar_one_or_none()

    assert avatar is not None, "Annie avatar record missing in database"
    assert avatar.name == "Annie - Studio Presenter"
    assert avatar.preview_asset_id is not None, "Annie preview asset missing"

    asset = await db_session.get(Asset, avatar.preview_asset_id)
    assert asset is not None, "Annie avatar preview Asset missing"
    assert "annie_studio_presenter.jpg" in asset.storage_key

    storage = get_storage_provider()
    assert storage.object_exists(asset.storage_key), f"Avatar asset object missing in MinIO: {asset.storage_key}"


@pytest.mark.asyncio
async def test_annie_voice_resolution_in_speech_orchestrator(db_session, test_workspace):
    """Verify ProjectSpeechOrchestrator resolves Annie voice ID to piper and en_US-lessac-medium."""
    orchestrator = ProjectSpeechOrchestrator(db_session)
    voice, provider_name, provider_ref = await orchestrator._resolve_voice(
        voice_id="10000000-0000-0000-0000-000000000003",
        workspace_id=test_workspace.id,
        is_mock_mode=False,
    )

    assert provider_name == "piper"
    assert provider_ref == "en_US-lessac-medium"
    assert voice.name == "Annie - Lifelike"


@pytest.mark.asyncio
async def test_daniel_regression_resolution(db_session, test_workspace):
    """Verify Daniel avatar and voice regression resolution."""
    # Daniel avatar
    stmt = select(Avatar).where(Avatar.id == uuid.UUID("30000000-0000-0000-0000-000000000004"))
    res = await db_session.execute(stmt)
    avatar = res.scalar_one_or_none()
    assert avatar is not None
    assert avatar.name == "Daniel - Modern Creator"

    # Daniel voice
    orchestrator = ProjectSpeechOrchestrator(db_session)
    voice, provider_name, provider_ref = await orchestrator._resolve_voice(
        voice_id="en_US-lessac-medium",
        workspace_id=test_workspace.id,
        is_mock_mode=False,
    )
    assert provider_name == "piper"
    assert provider_ref == "en_US-lessac-medium"
