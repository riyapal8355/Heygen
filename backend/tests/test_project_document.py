"""Unit tests for ProjectDocumentV1 schema validation and default factory."""

import pytest
from pydantic import ValidationError

from app.schemas.project_document import (
    CanvasSettings,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    create_default_project_document,
)


def test_valid_project_document_v1():
    """Verify standard ProjectDocumentV1 parses successfully."""
    doc = ProjectDocumentV1(
        schema_version=1,
        settings=ProjectSettings(
            aspect_ratio="16:9",
            width=1920,
            height=1080,
            fps=30,
            total_duration=10.0,
        ),
        scenes=[
            Scene(
                id="scene-1",
                sequence=1,
                duration=5.0,
                background={"type": "color", "value": "#1E293B"},
            ),
            Scene(
                id="scene-2",
                sequence=2,
                duration=5.0,
                background={"type": "color", "value": "#0F172A"},
            ),
        ],
        audio_tracks=[],
        assets=[],
        metadata={"author": "AI Director", "custom_tag": 123},
    )
    assert doc.schema_version == 1
    assert len(doc.scenes) == 2
    assert doc.metadata["author"] == "AI Director"


def test_unsupported_schema_version_rejected():
    """Verify invalid schema_version triggers validation error."""
    with pytest.raises(ValidationError):
        ProjectDocumentV1(schema_version=2)  # type: ignore

    with pytest.raises(ValidationError):
        ProjectDocumentV1(schema_version=0)  # type: ignore


def test_invalid_settings_rejected():
    """Verify invalid canvas dimensions or fps are rejected."""
    with pytest.raises(ValidationError):
        ProjectSettings(width=50)  # below 128 minimum

    with pytest.raises(ValidationError):
        ProjectSettings(fps=0)  # below 1 minimum


def test_create_default_project_document_factory():
    """Verify helper factory creates initialized, valid ProjectDocumentV1."""
    doc = create_default_project_document(
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        fps=60,
        initial_title="TikTok Promo",
    )
    assert doc.schema_version == 1
    assert doc.settings.aspect_ratio == "9:16"
    assert doc.settings.width == 1080
    assert doc.settings.height == 1920
    assert doc.settings.fps == 60
    assert len(doc.scenes) == 1
    assert doc.metadata["title"] == "TikTok Promo"
