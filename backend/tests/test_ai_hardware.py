"""Unit and functional tests for cross-platform safe hardware detection."""

import os
import platform
import pytest

from app.ai.hardware import (
    CPUSpec,
    DiskSpec,
    GPUSpec,
    HardwareSpec,
    HardwareState,
    MemorySpec,
    detect_hardware,
)


def test_detect_hardware_on_current_host():
    """Verify hardware detection executes cleanly on host without throwing exceptions."""
    hw = detect_hardware(refresh=True)

    assert hw.os_name in ("Windows", "Linux", "Darwin")
    assert hw.cpu.logical_cores >= 1
    assert hw.cpu.physical_cores >= 1
    assert len(hw.cpu.model) > 0
    assert hw.memory.ram_total_bytes > 0
    assert hw.memory.ram_available_bytes > 0
    assert hw.disk.disk_total_bytes > 0

    # Current machine verification
    if platform.system() == "Windows" and "AMD" in hw.cpu.model:
        # On this machine we know there is no NVIDIA CUDA GPU
        assert hw.gpu.cuda_available is False


def test_hardware_compatibility_cpu_model():
    """Verify hardware compatibility evaluation for CPU-capable models."""
    hw = detect_hardware()
    # 256MB RAM requirement should easily pass on any host with >= 1GB
    is_compat, state, reason = hw.check_model_compatibility(
        minimum_ram_bytes=256 * 1024 * 1024,
        requires_gpu=False,
    )
    assert is_compat is True
    assert state == HardwareState.AVAILABLE


def test_hardware_compatibility_gpu_required_on_non_cuda_host():
    """Verify that a GPU-required model fails compatibility gracefully on a non-CUDA host."""
    hw = detect_hardware()
    if not hw.gpu.cuda_available:
        is_compat, state, reason = hw.check_model_compatibility(
            minimum_ram_bytes=1024 * 1024,
            requires_gpu=True,
            minimum_vram_bytes=2 * 1024 * 1024 * 1024,
        )
        assert is_compat is False
        assert state == HardwareState.REQUIRES_GPU
        assert "CUDA" in reason


def test_hardware_compatibility_insufficient_ram():
    """Verify that a model requiring more RAM than total host memory reports INSUFFICIENT_MEMORY."""
    hw = detect_hardware()
    insane_ram = hw.memory.ram_total_bytes + (100 * 1024 * 1024 * 1024)  # host RAM + 100GB
    is_compat, state, reason = hw.check_model_compatibility(
        minimum_ram_bytes=insane_ram,
        requires_gpu=False,
    )
    assert is_compat is False
    assert state == HardwareState.INSUFFICIENT_MEMORY
    assert "RAM" in reason


def test_simulated_cuda_hardware_compatibility():
    """Verify simulated CUDA-capable hardware satisfies GPU model requirements."""
    simulated_hw = HardwareSpec(
        os_name="Linux",
        os_release="22.04",
        os_version="5.15.0",
        python_version="3.12.0",
        cpu=CPUSpec(
            model="Intel Xeon Gold",
            architecture="x86_64",
            physical_cores=16,
            logical_cores=32,
        ),
        gpu=GPUSpec(
            has_gpu=True,
            gpu_count=1,
            vendor="NVIDIA",
            model="NVIDIA RTX 4096",
            vram_total_bytes=16 * 1024 * 1024 * 1024,
            vram_free_bytes=14 * 1024 * 1024 * 1024,
            cuda_available=True,
            cuda_version="12.4",
            driver_version="550.54.14",
        ),
        memory=MemorySpec(
            ram_total_bytes=64 * 1024 * 1024 * 1024,
            ram_available_bytes=48 * 1024 * 1024 * 1024,
        ),
        disk=DiskSpec(
            disk_total_bytes=500 * 1024 * 1024 * 1024,
            disk_free_bytes=300 * 1024 * 1024 * 1024,
        ),
        docker_gpu_available=True,
    )

    # 1. GPU model with 8GB VRAM
    is_compat, state, reason = simulated_hw.check_model_compatibility(
        minimum_ram_bytes=16 * 1024 * 1024 * 1024,
        requires_gpu=True,
        minimum_vram_bytes=8 * 1024 * 1024 * 1024,
    )
    assert is_compat is True
    assert state == HardwareState.AVAILABLE

    # 2. Insufficient VRAM test (requesting 24GB on 16GB GPU)
    is_compat_2, state_2, reason_2 = simulated_hw.check_model_compatibility(
        minimum_ram_bytes=8 * 1024 * 1024 * 1024,
        requires_gpu=True,
        minimum_vram_bytes=24 * 1024 * 1024 * 1024,
    )
    assert is_compat_2 is False
    assert state_2 == HardwareState.INSUFFICIENT_MEMORY
    assert "VRAM" in reason_2
