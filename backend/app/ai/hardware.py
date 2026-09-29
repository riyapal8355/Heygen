"""Cross-platform safe hardware and resource detection.

Safely detects CPU, system RAM, GPU, VRAM, CUDA capabilities, Docker GPU support,
and disk storage without failing on machines lacking dedicated GPUs or CUDA.
Supports Windows, Linux, macOS, WSL, and Docker container environments.
"""

from enum import Enum
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class HardwareState(str, Enum):
    """Resource availability and compatibility states."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    REQUIRES_GPU = "REQUIRES_GPU"
    INSUFFICIENT_MEMORY = "INSUFFICIENT_MEMORY"
    INCOMPATIBLE = "INCOMPATIBLE"


class CPUSpec(BaseModel):
    """CPU architecture and core capabilities."""
    model: str = Field(..., description="CPU model/processor identifier")
    architecture: str = Field(..., description="CPU architecture, e.g. AMD64, x86_64, arm64")
    physical_cores: int = Field(1, ge=1, description="Physical CPU cores count")
    logical_cores: int = Field(1, ge=1, description="Logical/hyperthreaded CPU cores count")


class GPUSpec(BaseModel):
    """GPU accelerator and CUDA capability descriptor."""
    has_gpu: bool = Field(False, description="Whether any display adapter or discrete GPU is present")
    gpu_count: int = Field(0, ge=0, description="Total number of discrete or integrated GPUs")
    vendor: str = Field("None", description="Primary GPU vendor: NVIDIA, AMD, Intel, Apple, or None")
    model: str = Field("None", description="GPU marketing model name")
    vram_total_bytes: int = Field(0, ge=0, description="Total GPU VRAM in bytes")
    vram_free_bytes: int = Field(0, ge=0, description="Currently free GPU VRAM in bytes")
    cuda_available: bool = Field(False, description="Whether NVIDIA CUDA acceleration is operational")
    cuda_version: Optional[str] = Field(None, description="Detected CUDA toolkit/runtime version")
    driver_version: Optional[str] = Field(None, description="GPU driver version string")
    compute_capability: Optional[str] = Field(None, description="Detected CUDA compute capability (e.g. 7.5, 8.6, 8.9)")
    device_index: int = Field(0, ge=0, description="Primary CUDA device index")

    @property
    def vram_total_gb(self) -> float:
        return round(self.vram_total_bytes / (1024 ** 3), 2)

    @property
    def vram_free_gb(self) -> float:
        return round(self.vram_free_bytes / (1024 ** 3), 2)


class MemorySpec(BaseModel):
    """System volatile memory (RAM) capacity and availability."""
    ram_total_bytes: int = Field(..., ge=0, description="Total physical RAM in bytes")
    ram_available_bytes: int = Field(..., ge=0, description="Currently available physical RAM in bytes")

    @property
    def ram_total_gb(self) -> float:
        return round(self.ram_total_bytes / (1024 ** 3), 2)

    @property
    def ram_available_gb(self) -> float:
        return round(self.ram_available_bytes / (1024 ** 3), 2)


class DiskSpec(BaseModel):
    """Persistent storage disk capacity and availability."""
    disk_total_bytes: int = Field(..., ge=0, description="Total disk partition space in bytes")
    disk_free_bytes: int = Field(..., ge=0, description="Available disk space in bytes")

    @property
    def disk_total_gb(self) -> float:
        return round(self.disk_total_bytes / (1024 ** 3), 2)

    @property
    def disk_free_gb(self) -> float:
        return round(self.disk_free_bytes / (1024 ** 3), 2)


class HardwareSpec(BaseModel):
    """Complete host environment hardware and resource descriptor."""
    os_name: str = Field(..., description="Operating system family: Windows, Linux, Darwin")
    os_release: str = Field(..., description="OS release version, e.g. 11, 22.04")
    os_version: str = Field(..., description="OS detailed kernel/build version")
    python_version: str = Field(..., description="Host Python runtime version")
    cpu: CPUSpec
    gpu: GPUSpec
    memory: MemorySpec
    disk: DiskSpec
    docker_gpu_available: Optional[bool] = Field(None, description="Whether Docker has nvidia-container-toolkit enabled")

    @property
    def has_cuda(self) -> bool:
        """Convenience accessor for CUDA GPU acceleration availability."""
        return bool(self.gpu.cuda_available)

    def check_model_compatibility(

        self,
        minimum_ram_bytes: int = 0,
        requires_gpu: bool = False,
        minimum_vram_bytes: Optional[int] = None,
    ) -> Tuple[bool, HardwareState, str]:
        """Evaluate whether this host hardware satisfies model execution requirements.

        Returns:
            (is_compatible, state, reason)
        """
        # 1. GPU Check
        if requires_gpu:
            if not self.gpu.cuda_available:
                return (
                    False,
                    HardwareState.REQUIRES_GPU,
                    f"Model requires NVIDIA CUDA GPU, but none is operational (vendor: {self.gpu.vendor}, cuda: {self.gpu.cuda_available})",
                )
            if minimum_vram_bytes and self.gpu.vram_total_bytes < minimum_vram_bytes:
                req_gb = round(minimum_vram_bytes / (1024 ** 3), 2)
                return (
                    False,
                    HardwareState.INSUFFICIENT_MEMORY,
                    f"Model requires {req_gb} GB VRAM, but GPU has only {self.gpu.vram_total_gb} GB total VRAM",
                )

        # 2. System RAM Check
        if minimum_ram_bytes > 0:
            if self.memory.ram_total_bytes < minimum_ram_bytes:
                req_gb = round(minimum_ram_bytes / (1024 ** 3), 2)
                return (
                    False,
                    HardwareState.INSUFFICIENT_MEMORY,
                    f"Model requires {req_gb} GB system RAM, but host has only {self.memory.ram_total_gb} GB total RAM",
                )

        return True, HardwareState.AVAILABLE, "Host hardware meets model requirements"


# ---------------------------------------------------------------------------
# Platform-Safe Detection Implementations
# ---------------------------------------------------------------------------

def _detect_cpu() -> CPUSpec:
    """Detect CPU architecture, model name, and core counts."""
    logical = os.cpu_count() or 1
    arch = platform.machine() or "unknown"
    model = platform.processor() or arch

    # Windows registry lookup for clean marketing model name
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if val and isinstance(val, str):
                model = val.strip()
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "model name" in line:
                            model = line.split(":", 1)[1].strip()
                            break
        except Exception:
            pass

    # Physical core estimation (standard fallback: half of logical if multithreaded)
    physical = max(1, logical // 2) if logical > 1 else 1

    return CPUSpec(
        model=model,
        architecture=arch,
        physical_cores=physical,
        logical_cores=logical,
    )


def _detect_memory() -> MemorySpec:
    """Detect total and available physical RAM."""
    # 1. Windows GlobalMemoryStatusEx via ctypes
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return MemorySpec(
                    ram_total_bytes=int(stat.ullTotalPhys),
                    ram_available_bytes=int(stat.ullAvailPhys),
                )
        except Exception as exc:
            logger.debug("Win32 memory detection failed: %s", exc)

    # 2. Linux /proc/meminfo
    if sys.platform.startswith("linux") and os.path.exists("/proc/meminfo"):
        try:
            total_kb = 0
            avail_kb = 0
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_str = parts[1].strip().split()[0]
                        if key == "MemTotal":
                            total_kb = int(val_str)
                        elif key in ("MemAvailable", "MemFree") and avail_kb == 0:
                            avail_kb = int(val_str)
            if total_kb > 0:
                return MemorySpec(
                    ram_total_bytes=total_kb * 1024,
                    ram_available_bytes=(avail_kb or total_kb // 2) * 1024,
                )
        except Exception as exc:
            logger.debug("Linux /proc/meminfo read failed: %s", exc)

    # 3. macOS or POSIX sysconf fallback
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = pages * page_size
        return MemorySpec(ram_total_bytes=total, ram_available_bytes=total // 2)
    except Exception:
        pass

    # Conservative default (4GB)
    default_ram = 4 * 1024 * 1024 * 1024
    return MemorySpec(ram_total_bytes=default_ram, ram_available_bytes=default_ram // 2)


def _detect_gpu() -> GPUSpec:
    """Detect GPU hardware, VRAM, and CUDA capability safely without throwing exceptions."""
    # 1. Attempt nvidia-smi detection
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi and sys.platform == "win32":
        common_win_nvsmi = os.path.join(
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            r"NVIDIA Corporation\NVSMI\nvidia-smi.exe",
        )
        if os.path.exists(common_win_nvsmi):
            nvidia_smi = common_win_nvsmi

    if nvidia_smi:
        try:
            cmd = [
                nvidia_smi,
                "--query-gpu=name,memory.total,memory.free,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                lines = [l.strip() for l in proc.stdout.strip().splitlines() if l.strip()]
                if lines:
                    parts = [p.strip() for p in lines[0].split(",")]
                    if len(parts) >= 4:
                        name = parts[0]
                        total_mb = int(float(parts[1]))
                        free_mb = int(float(parts[2]))
                        driver_ver = parts[3]
                        compute_cap = parts[4].strip() if len(parts) >= 5 else None

                        # Detect CUDA version if available
                        cuda_ver = None
                        nvcc = shutil.which("nvcc")
                        if nvcc:
                            try:
                                nvcc_proc = subprocess.run(
                                    [nvcc, "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=2,
                                    check=False,
                                    )
                                for line in nvcc_proc.stdout.splitlines():
                                    if "release" in line:
                                        cuda_ver = line.split("release")[-1].split(",")[0].strip()
                            except Exception:
                                pass

                        return GPUSpec(
                            has_gpu=True,
                            gpu_count=len(lines),
                            vendor="NVIDIA",
                            model=name,
                            vram_total_bytes=total_mb * 1024 * 1024,
                            vram_free_bytes=free_mb * 1024 * 1024,
                            cuda_available=True,
                            cuda_version=cuda_ver,
                            driver_version=driver_ver,
                            compute_capability=compute_cap,
                            device_index=0,
                        )
        except Exception as exc:
            logger.debug("nvidia-smi execution encountered error: %s", exc)

    # 2. PyTorch optional check if installed
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            name = torch.cuda.get_device_name(0) if count > 0 else "NVIDIA GPU"
            props = torch.cuda.get_device_properties(0) if count > 0 else None
            total_bytes = props.total_memory if props else 0
            cap_str = f"{props.major}.{props.minor}" if props and hasattr(props, "major") else None
            cuda_ver = getattr(torch.version, "cuda", None)
            return GPUSpec(
                has_gpu=True,
                gpu_count=count,
                vendor="NVIDIA",
                model=name,
                vram_total_bytes=total_bytes,
                vram_free_bytes=total_bytes,  # approximate initial
                cuda_available=True,
                cuda_version=cuda_ver,
                driver_version=None,
                compute_capability=cap_str,
                device_index=0,
            )
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("torch cuda check error: %s", exc)

    # 3. Non-NVIDIA GPU Detection on Windows (e.g. AMD Radeon, Intel Iris/UHD)
    if sys.platform == "win32":
        try:
            # Query PowerShell Get-CimInstance Win32_VideoController
            ps_cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ]
            proc = subprocess.run(
                ps_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                gpus = [g.strip() for g in proc.stdout.strip().splitlines() if g.strip()]
                # Exclude virtual / remote display hooks if hardware GPU is present
                real_gpus = [g for g in gpus if "virtual" not in g.lower()]
                selected = real_gpus[0] if real_gpus else gpus[0]

                vendor = "Unknown"
                if "amd" in selected.lower() or "radeon" in selected.lower():
                    vendor = "AMD"
                elif "intel" in selected.lower():
                    vendor = "Intel"
                elif "nvidia" in selected.lower():
                    vendor = "NVIDIA"

                return GPUSpec(
                    has_gpu=True,
                    gpu_count=len(gpus),
                    vendor=vendor,
                    model=selected,
                    vram_total_bytes=512 * 1024 * 1024,  # Standard shared minimum estimate
                    vram_free_bytes=512 * 1024 * 1024,
                    cuda_available=False,
                    cuda_version=None,
                    driver_version=None,
                )
        except Exception as exc:
            logger.debug("Win32 video controller query failed: %s", exc)

    # 4. Fallback: No discrete/supported GPU
    return GPUSpec(
        has_gpu=False,
        gpu_count=0,
        vendor="None",
        model="None",
        vram_total_bytes=0,
        vram_free_bytes=0,
        cuda_available=False,
        cuda_version=None,
        driver_version=None,
    )


def _detect_disk(path: Optional[str] = None) -> DiskSpec:
    """Detect storage volume capacity and free space."""
    target_path = path or os.path.abspath(".")
    try:
        usage = shutil.disk_usage(target_path)
        return DiskSpec(
            disk_total_bytes=usage.total,
            disk_free_bytes=usage.free,
        )
    except Exception:
        # Fallback 100GB
        gb100 = 100 * 1024 * 1024 * 1024
        return DiskSpec(disk_total_bytes=gb100, disk_free_bytes=gb100 // 2)


def _detect_docker_gpu() -> Optional[bool]:
    """Check if Docker runtime has NVIDIA container support enabled."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return None
    try:
        proc = subprocess.run(
            [docker_bin, "info", "--format", "{{json .Runtimes}}"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0 and "nvidia" in proc.stdout.lower():
            return True
        return False
    except Exception:
        return None


# Global cached hardware specification
_cached_hardware_spec: Optional[HardwareSpec] = None


def detect_hardware(refresh: bool = False, disk_path: Optional[str] = None) -> HardwareSpec:
    """Detect and return host hardware capabilities.

    Results are cached in memory unless refresh=True is specified.
    """
    global _cached_hardware_spec
    if _cached_hardware_spec is None or refresh:
        spec = HardwareSpec(
            os_name=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            python_version=platform.python_version(),
            cpu=_detect_cpu(),
            gpu=_detect_gpu(),
            memory=_detect_memory(),
            disk=_detect_disk(disk_path),
            docker_gpu_available=_detect_docker_gpu(),
        )
        _cached_hardware_spec = spec
        logger.info(
            "Detected host hardware: OS=%s, CPU=%s (%d cores), RAM=%.2f GB, GPU=%s (CUDA=%s)",
            spec.os_name,
            spec.cpu.model,
            spec.cpu.logical_cores,
            spec.memory.ram_total_gb,
            spec.gpu.model,
            spec.gpu.cuda_available,
        )
    return _cached_hardware_spec


class GPUErrorCode(str, Enum):
    """Standardized error codes for GPU hardware and runtime admission failures."""
    GPU_UNAVAILABLE = "GPU_UNAVAILABLE"
    GPU_DRIVER_UNAVAILABLE = "GPU_DRIVER_UNAVAILABLE"
    GPU_CUDA_UNAVAILABLE = "GPU_CUDA_UNAVAILABLE"
    GPU_COMPUTE_CAPABILITY_UNSUPPORTED = "GPU_COMPUTE_CAPABILITY_UNSUPPORTED"
    GPU_VRAM_INSUFFICIENT = "GPU_VRAM_INSUFFICIENT"
    GPU_RUNTIME_MISMATCH = "GPU_RUNTIME_MISMATCH"
    GPU_MODEL_MISSING = "GPU_MODEL_MISSING"
    GPU_DEPENDENCY_MISSING = "GPU_DEPENDENCY_MISSING"
    GPU_BUSY = "GPU_BUSY"


class GPUAdmissionResult(BaseModel):
    """Canonical hardware admission descriptor for GPU worker runtime."""
    available: bool = Field(False, description="Whether an NVIDIA GPU is available and operational")
    device_name: Optional[str] = Field(None, description="GPU device model name")
    device_index: int = Field(0, description="Device index")
    compute_capability: Optional[str] = Field(None, description="Compute capability version, e.g. 8.6")
    total_vram_mb: int = Field(0, description="Total VRAM in MB")
    free_vram_mb: int = Field(0, description="Free VRAM in MB")
    cuda_version: Optional[str] = Field(None, description="CUDA runtime version")
    torch_version: Optional[str] = Field(None, description="PyTorch version")
    driver_version: Optional[str] = Field(None, description="NVIDIA driver version")
    supported: bool = Field(False, description="Whether GPU meets admission criteria")
    reason: str = Field(..., description="Human-readable admission decision reason")
    error_code: Optional[GPUErrorCode] = Field(None, description="Standardized error code if not supported")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic telemetry")

    def __iter__(self):
        """Enable tuple unpacking (admitted, reason, details) for backward compatibility."""
        yield self.supported
        yield self.reason
        yield self.details

    def __getitem__(self, item: int):
        """Enable index-based access (result[0], result[1], result[2]) for backward compatibility."""
        return (self.supported, self.reason, self.details)[item]


def check_gpu_admission(
    min_vram_gb: float = 8.0,
    min_compute_capability: float = 7.0,
    device_index: int = 0,
    spec: Optional[HardwareSpec] = None,
) -> GPUAdmissionResult:
    """Strict hardware admission check for GPU worker container.

    Enforces:
    1. NVIDIA GPU presence
    2. NVIDIA driver is visible
    3. CUDA is available
    4. Torch CUDA is operational (in live host mode)
    5. GPU device is compatible (compute capability >= min_compute_capability)
    6. Required VRAM is available (total VRAM >= min_vram_gb)

    Returns:
        GPUAdmissionResult (supports backward-compatible unpacking: admitted, reason, details)
    """
    is_simulated = (spec is not None)
    hw = spec or detect_hardware()
    gpu = hw.gpu

    torch_ver = None
    try:
        import torch
        torch_ver = getattr(torch, "__version__", None)
    except ImportError:
        pass

    total_vram_mb = int(gpu.vram_total_bytes / (1024 * 1024))
    free_vram_mb = int(gpu.vram_free_bytes / (1024 * 1024))

    details: Dict[str, Any] = {
        "has_gpu": gpu.has_gpu,
        "vendor": gpu.vendor,
        "model": gpu.model,
        "driver_version": gpu.driver_version,
        "cuda_version": gpu.cuda_version,
        "cuda_available": gpu.cuda_available,
        "compute_capability": gpu.compute_capability,
        "vram_total_gb": gpu.vram_total_gb,
        "vram_free_gb": gpu.vram_free_gb,
        "min_vram_gb": min_vram_gb,
        "min_compute_capability": min_compute_capability,
        "device_index": device_index,
        "is_simulated": is_simulated,
    }

    # 1. NVIDIA GPU presence
    if not gpu.has_gpu or gpu.vendor != "NVIDIA":
        reason = f"GPU_UNAVAILABLE: No NVIDIA GPU detected on host (vendor={gpu.vendor}, model={gpu.model})."
        details["error_code"] = GPUErrorCode.GPU_UNAVAILABLE.value
        return GPUAdmissionResult(
            available=False,
            device_name=gpu.model if gpu.has_gpu else None,
            device_index=device_index,
            compute_capability=gpu.compute_capability,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            cuda_version=gpu.cuda_version,
            torch_version=torch_ver,
            driver_version=gpu.driver_version,
            supported=False,
            reason=reason,
            error_code=GPUErrorCode.GPU_UNAVAILABLE,
            details=details,
        )

    # 2. NVIDIA driver visibility
    if not gpu.driver_version:
        reason = "GPU_UNAVAILABLE: NVIDIA GPU driver is not visible or accessible."
        details["error_code"] = GPUErrorCode.GPU_DRIVER_UNAVAILABLE.value
        return GPUAdmissionResult(
            available=False,
            device_name=gpu.model,
            device_index=device_index,
            compute_capability=gpu.compute_capability,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            cuda_version=gpu.cuda_version,
            torch_version=torch_ver,
            driver_version=None,
            supported=False,
            reason=reason,
            error_code=GPUErrorCode.GPU_DRIVER_UNAVAILABLE,
            details=details,
        )

    # 3. CUDA availability
    if not gpu.cuda_available:
        reason = "GPU_UNAVAILABLE: CUDA acceleration is not operational."
        details["error_code"] = GPUErrorCode.GPU_CUDA_UNAVAILABLE.value
        return GPUAdmissionResult(
            available=False,
            device_name=gpu.model,
            device_index=device_index,
            compute_capability=gpu.compute_capability,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            cuda_version=gpu.cuda_version,
            torch_version=torch_ver,
            driver_version=gpu.driver_version,
            supported=False,
            reason=reason,
            error_code=GPUErrorCode.GPU_CUDA_UNAVAILABLE,
            details=details,
        )

    # 4. Torch CUDA check (strictly in live host mode; skipped when evaluating simulated spec)
    if not is_simulated:
        try:
            import torch
            if not torch.cuda.is_available():
                reason = "GPU_UNAVAILABLE: PyTorch is installed but torch.cuda.is_available() is False."
                details["error_code"] = GPUErrorCode.GPU_CUDA_UNAVAILABLE.value
                return GPUAdmissionResult(
                    available=False,
                    device_name=gpu.model,
                    device_index=device_index,
                    compute_capability=gpu.compute_capability,
                    total_vram_mb=total_vram_mb,
                    free_vram_mb=free_vram_mb,
                    cuda_version=gpu.cuda_version,
                    torch_version=torch_ver,
                    driver_version=gpu.driver_version,
                    supported=False,
                    reason=reason,
                    error_code=GPUErrorCode.GPU_CUDA_UNAVAILABLE,
                    details=details,
                )
        except ImportError:
            details["torch_installed"] = False

    # 5. Required VRAM check
    min_vram_bytes = int(min_vram_gb * 1024 * 1024 * 1024)
    if gpu.vram_total_bytes < min_vram_bytes:
        reason = (
            f"GPU_VRAM_INSUFFICIENT (GPU_INSUFFICIENT_VRAM, INSUFFICIENT_VRAM): Host has {gpu.vram_total_gb} GB VRAM, "
            f"but at least {min_vram_gb} GB is required."
        )
        details["error_code"] = GPUErrorCode.GPU_VRAM_INSUFFICIENT.value
        return GPUAdmissionResult(
            available=True,
            device_name=gpu.model,
            device_index=device_index,
            compute_capability=gpu.compute_capability,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            cuda_version=gpu.cuda_version,
            torch_version=torch_ver,
            driver_version=gpu.driver_version,
            supported=False,
            reason=reason,
            error_code=GPUErrorCode.GPU_VRAM_INSUFFICIENT,
            details=details,
        )

    # 6. Compute capability check
    if gpu.compute_capability:
        try:
            cap_val = float(gpu.compute_capability)
            if cap_val < min_compute_capability:
                reason = (
                    f"GPU_COMPUTE_CAPABILITY_UNSUPPORTED (GPU_INCOMPATIBLE): Compute capability "
                    f"{gpu.compute_capability} is below required {min_compute_capability}."
                )
                details["error_code"] = GPUErrorCode.GPU_COMPUTE_CAPABILITY_UNSUPPORTED.value
                return GPUAdmissionResult(
                    available=True,
                    device_name=gpu.model,
                    device_index=device_index,
                    compute_capability=gpu.compute_capability,
                    total_vram_mb=total_vram_mb,
                    free_vram_mb=free_vram_mb,
                    cuda_version=gpu.cuda_version,
                    torch_version=torch_ver,
                    driver_version=gpu.driver_version,
                    supported=False,
                    reason=reason,
                    error_code=GPUErrorCode.GPU_COMPUTE_CAPABILITY_UNSUPPORTED,
                    details=details,
                )
        except (ValueError, TypeError):
            pass

    reason = "ADMITTED: Host satisfies all GPU worker hardware requirements."
    details["error_code"] = None
    return GPUAdmissionResult(
        available=True,
        device_name=gpu.model,
        device_index=device_index,
        compute_capability=gpu.compute_capability,
        total_vram_mb=total_vram_mb,
        free_vram_mb=free_vram_mb,
        cuda_version=gpu.cuda_version,
        torch_version=torch_ver,
        driver_version=gpu.driver_version,
        supported=True,
        reason=reason,
        error_code=None,
        details=details,
    )


def get_neural_avatar_hardware_status() -> Dict[str, Any]:
    """Return comprehensive neural avatar hardware capability descriptor conforming to Section 8."""
    hw = detect_hardware()
    cuda = hw.gpu.cuda_available
    vram = hw.gpu.vram_total_gb
    gpu_name = f"{hw.gpu.vendor} {hw.gpu.model}".strip()

    directml_avail = False
    if hw.os_name.lower() == "windows":
        try:
            import onnxruntime as ort
            directml_avail = "DmlExecutionProvider" in ort.get_available_providers()
        except Exception:
            directml_avail = False

    return {
        "cuda_available": cuda,
        "gpu_name": gpu_name,
        "vram_gb": vram,
        "directml_available": directml_avail,
        "liveportrait": {
            "available": bool(cuda and vram >= 4.0),
            "reason": "Ready" if (cuda and vram >= 4.0) else "CUDA GPU required",
            "required_vram_gb": 4.0,
        },
        "musetalk": {
            "available": bool(cuda and vram >= 4.0),
            "reason": "Ready" if (cuda and vram >= 4.0) else "CUDA GPU required",
            "required_vram_gb": 4.0,
        },
        "hallo2": {
            "available": bool(cuda and vram >= 8.0),
            "reason": "Ready" if (cuda and vram >= 8.0) else "CUDA GPU required",
            "required_vram_gb": 8.0,
        },
        "wav2lip": {
            "available": True,
            "reason": "Available (CPU Development Fallback)",
        },
    }


