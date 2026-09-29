"""Unit tests for MediaWorkspace scratch filesystem lifecycle and asset resolution."""

import uuid
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.media.errors import RenderInputMissingError
from app.media.workspace import MediaWorkspace
from app.models.asset import Asset


def test_media_workspace_structure_and_cleanup():
    """Verify MediaWorkspace creates standard directory hierarchy and cleans up."""
    captured_root: Path
    with MediaWorkspace(prefix="test_ws_") as mws:
        captured_root = mws.root_path
        assert captured_root.exists()
        assert mws.inputs_dir.exists()
        assert mws.scenes_dir.exists()
        assert mws.audio_dir.exists()
        assert mws.output_dir.exists()

        dummy_file = mws.inputs_dir / "test.txt"
        dummy_file.write_text("sample")
        assert dummy_file.exists()

    assert not captured_root.exists()


@pytest.mark.asyncio
async def test_media_workspace_resolve_asset_missing():
    """Verify resolve_asset raises RenderInputMissingError when asset does not exist."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    db.execute.return_value = mock_result

    with MediaWorkspace() as mws:
        with pytest.raises(RenderInputMissingError) as exc:
            await mws.resolve_asset(
                asset_id=uuid.uuid4(),
                workspace_id=uuid.uuid4(),
                db=db,
            )
        assert exc.value.code == "RENDER_INPUT_MISSING"


@pytest.mark.asyncio
async def test_media_workspace_resolve_asset_not_ready():
    """Verify resolve_asset raises RenderInputMissingError when asset status is not ready."""
    ws_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        status="processing",
        storage_key="dummy_key",
        original_filename="sample.mp4",
        asset_type="video",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = asset
    db.execute.return_value = mock_result

    with MediaWorkspace() as mws:
        with pytest.raises(RenderInputMissingError) as exc:
            await mws.resolve_asset(
                asset_id=asset_id,
                workspace_id=ws_id,
                db=db,
            )
        assert "ready" in str(exc.value)


@pytest.mark.asyncio
async def test_media_workspace_resolve_asset_success():
    """Verify resolve_asset downloads and returns valid cached path."""
    ws_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        workspace_id=ws_id,
        status="ready",
        storage_key=f"workspaces/{ws_id}/assets/{asset_id}/test.wav",
        original_filename="test.wav",
        asset_type="audio",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = asset
    db.execute.return_value = mock_result

    # Mock storage provider
    storage_provider = MagicMock()

    def fake_download(key, dest):
        Path(dest).write_text("RIFFfakeaudioWAVE")

    storage_provider.download_file.side_effect = fake_download

    with MediaWorkspace() as mws:
        resolved_path = await mws.resolve_asset(
            asset_id=asset_id,
            workspace_id=ws_id,
            db=db,
            storage_provider=storage_provider,
        )
        assert resolved_path.exists()
        assert resolved_path.stat().st_size > 0
        assert resolved_path.parent == mws.inputs_dir
