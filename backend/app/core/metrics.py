"""Production metrics registry and telemetry abstraction for HeyZen.

Collects in-memory counters, histograms, and subsystem health indicators without
requiring heavyweight external dependencies.
"""

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class MetricsRegistry:
    """Thread-safe metrics registry for API, jobs, media pipeline, and storage."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()

        # API Metrics
        self._api_requests_total: int = 0
        self._api_errors_total: int = 0
        self._api_status_counts: Dict[int, int] = defaultdict(int)
        self._api_latencies: List[float] = []
        self._max_latency_samples = 1000

        # Job Metrics
        self._jobs_submitted_total: int = 0
        self._jobs_succeeded_total: int = 0
        self._jobs_failed_total: int = 0
        self._jobs_cancelled_total: int = 0
        self._job_durations: Dict[str, List[float]] = defaultdict(list)

        # AI & Media Pipeline
        self._ai_inference_counts: Dict[str, int] = defaultdict(int)
        self._ai_inference_durations: Dict[str, List[float]] = defaultdict(list)
        self._render_durations: List[float] = []

        # Subsystem Errors
        self._database_errors: int = 0
        self._redis_errors: int = 0
        self._storage_failures: int = 0

    def record_api_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        """Record an incoming HTTP request completion."""
        with self._lock:
            self._api_requests_total += 1
            self._api_status_counts[status_code] += 1
            if status_code >= 400:
                self._api_errors_total += 1
            self._api_latencies.append(duration_ms)
            if len(self._api_latencies) > self._max_latency_samples:
                self._api_latencies.pop(0)

    def record_job_submitted(self, job_type: str = "general") -> None:
        """Record job submission."""
        with self._lock:
            self._jobs_submitted_total += 1

    def record_job_finished(self, job_type: str, status: str, duration_seconds: Optional[float] = None) -> None:
        """Record job completion status transition."""
        with self._lock:
            if status == "succeeded":
                self._jobs_succeeded_total += 1
            elif status == "failed":
                self._jobs_failed_total += 1
            elif status == "cancelled":
                self._jobs_cancelled_total += 1

            if duration_seconds is not None:
                durations = self._job_durations[job_type]
                durations.append(duration_seconds)
                if len(durations) > 200:
                    durations.pop(0)

    def record_ai_inference(self, capability: str, provider: str, duration_seconds: float, success: bool = True) -> None:
        """Record AI inference invocation."""
        key = f"{capability}:{provider}"
        with self._lock:
            self._ai_inference_counts[key] += 1
            durations = self._ai_inference_durations[key]
            durations.append(duration_seconds)
            if len(durations) > 200:
                durations.pop(0)

    def record_render_duration(self, duration_seconds: float) -> None:
        """Record media rendering job duration."""
        with self._lock:
            self._render_durations.append(duration_seconds)
            if len(self._render_durations) > 200:
                self._render_durations.pop(0)

    def record_error(self, subsystem: str) -> None:
        """Increment error counter for a specific backend subsystem."""
        with self._lock:
            if subsystem == "database":
                self._database_errors += 1
            elif subsystem == "redis":
                self._redis_errors += 1
            elif subsystem == "storage":
                self._storage_failures += 1

    def get_snapshot(self) -> Dict[str, Any]:
        """Generate a complete telemetry snapshot."""
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            avg_api_latency = (
                sum(self._api_latencies) / len(self._api_latencies)
                if self._api_latencies
                else 0.0
            )
            p95_api_latency = (
                sorted(self._api_latencies)[int(len(self._api_latencies) * 0.95)]
                if len(self._api_latencies) >= 20
                else avg_api_latency
            )

            job_durations_summary = {}
            for jtype, durations in self._job_durations.items():
                if durations:
                    job_durations_summary[jtype] = {
                        "count": len(durations),
                        "avg_seconds": round(sum(durations) / len(durations), 3),
                        "max_seconds": round(max(durations), 3),
                    }

            return {
                "uptime_seconds": round(uptime_seconds, 1),
                "api": {
                    "requests_total": self._api_requests_total,
                    "errors_total": self._api_errors_total,
                    "status_counts": dict(self._api_status_counts),
                    "avg_latency_ms": round(avg_api_latency, 2),
                    "p95_latency_ms": round(p95_api_latency, 2),
                },
                "jobs": {
                    "submitted_total": self._jobs_submitted_total,
                    "succeeded_total": self._jobs_succeeded_total,
                    "failed_total": self._jobs_failed_total,
                    "cancelled_total": self._jobs_cancelled_total,
                    "durations_summary": job_durations_summary,
                },
                "ai": {
                    "inference_counts": dict(self._ai_inference_counts),
                },
                "subsystems": {
                    "database_errors": self._database_errors,
                    "redis_errors": self._redis_errors,
                    "storage_failures": self._storage_failures,
                },
            }


_global_metrics = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """Retrieve global metrics singleton."""
    return _global_metrics
