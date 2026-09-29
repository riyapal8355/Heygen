"""Unit tests for Celery task queue resolution and multi-queue routing."""

import pytest

from app.services.job_service import resolve_job_queue


def test_resolve_job_queue_media():
    """Verify video rendering routes to cpu_media queue."""
    assert resolve_job_queue("render_video") == "cpu_media"


def test_resolve_job_queue_maintenance():
    """Verify maintenance tasks route to maintenance queue."""
    assert resolve_job_queue("cleanup") == "maintenance"
    assert resolve_job_queue("maintenance.purge") == "maintenance"


def test_resolve_job_queue_cpu_friendly_ai():
    """Verify standard AI tasks with CPU compatibility route to cpu_media queue."""
    assert resolve_job_queue("tts_synthesis") == "cpu_media"
    assert resolve_job_queue("translate_project") == "cpu_media"
    assert resolve_job_queue("project_batch_speech") == "cpu_media"


def test_resolve_job_queue_explicit_cuda_device():
    """Verify tasks explicitly requesting CUDA route to gpu_ai queue."""
    assert resolve_job_queue("tts_synthesis", {"preferred_device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("tts_synthesis", {"device": "cuda"}) == "gpu_ai"
    assert resolve_job_queue("tts_synthesis", {"requires_gpu": True}) == "gpu_ai"


def test_resolve_job_queue_heavy_neural_tasks():
    """Verify heavy neural vision/avatar tasks route to gpu_ai by default and cpu_media on explicit CPU request."""
    # Defaults to gpu_ai
    assert resolve_job_queue("lip_sync") == "gpu_ai"
    assert resolve_job_queue("avatar_train") == "gpu_ai"
    assert resolve_job_queue("generate_scene_visual") == "gpu_ai"

    # Explicit CPU request routes to cpu_media
    assert resolve_job_queue("lip_sync", {"preferred_device": "cpu"}) == "cpu_media"
    assert resolve_job_queue("generate_scene_visual", {"device": "cpu"}) == "cpu_media"
