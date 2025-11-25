"""Performance monitoring utilities for Programgarden.

EN:
    Provides utilities to measure system resource usage (CPU, RAM) for the
    current process. It includes a snapshot function for on-demand checks
    and a context manager for measuring execution blocks.

KR:
    현재 프로세스의 시스템 자원 사용량(CPU, RAM)을 측정하는 유틸리티를 제공합니다.
    온디맨드 확인을 위한 스냅샷 기능과 실행 블록 측정을 위한 컨텍스트 매니저를
    포함합니다.
"""

import os
import time
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PerformanceStats:
    cpu_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    timestamp: float


class PerformanceMonitor:
    """Monitor system resources for the current process.

    EN:
        Wraps `psutil` to provide easy access to process-specific metrics.
    KR:
        `psutil`을 래핑하여 프로세스별 지표에 쉽게 접근할 수 있도록 합니다.
    """

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.cpu_core_count = psutil.cpu_count(logical=True) or 1
        # Initialize CPU measurement baseline
        self.process.cpu_percent(interval=None)

    def refresh_cpu_baseline(self) -> None:
        """Reset the internal CPU usage baseline without blocking."""
        self.process.cpu_percent(interval=None)

    def get_cpu_time(self) -> float:
        """Return accumulated user+system CPU time for the process."""
        times = self.process.cpu_times()
        return float(getattr(times, "user", 0.0) + getattr(times, "system", 0.0))

    def get_current_status(self, sample_interval: float = 0.0) -> Dict[str, Any]:
        """Get a snapshot of current resource usage.

        Args:
            sample_interval (float):
                EN: Optional blocking interval in seconds for CPU sampling.
                KR: CPU 샘플링을 위한 선택적 블로킹 시간(초)입니다.

        Returns:
            Dict[str, Any]: CPU percent, Memory usage (RSS, VMS in MB).
        """
        interval = sample_interval if sample_interval and sample_interval > 0 else None
        with self.process.oneshot():
            cpu_percent = self.process.cpu_percent(interval=interval)
            mem_info = self.process.memory_info()

        return {
            "cpu_percent": cpu_percent,
            "memory_rss_mb": round(mem_info.rss / 1024 / 1024, 2),
            "memory_vms_mb": round(mem_info.vms / 1024 / 1024, 2),
            "timestamp": time.time()
        }


class ExecutionTimer:
    """Context manager to measure execution time and resource delta.

    EN:
        Measures wall-clock time and resource usage changes across a code block.
    KR:
        코드 블록 전반에 걸친 실제 시간(wall-clock time)과 자원 사용량 변화를 측정합니다.
    """

    def __init__(self, monitor: PerformanceMonitor, sample_interval: float = 0.05):
        self.monitor = monitor
        self.sample_interval = max(sample_interval, 0.0)
        self.start_stats: Optional[Dict[str, Any]] = None
        self.end_stats: Optional[Dict[str, Any]] = None
        self.duration: float = 0.0
        self.start_cpu_time: float = 0.0
        self.end_cpu_time: float = 0.0

    def __enter__(self):
        self.monitor.refresh_cpu_baseline()
        self.start_stats = self.monitor.get_current_status(sample_interval=self.sample_interval)
        self.start_cpu_time = self.monitor.get_cpu_time()
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.end_cpu_time = self.monitor.get_cpu_time()
        self.monitor.refresh_cpu_baseline()
        self.end_stats = self.monitor.get_current_status(sample_interval=self.sample_interval)
        self.duration = self.end_time - self.start_time

    def get_result(self) -> Dict[str, Any]:
        if not self.start_stats or not self.end_stats:
            return {}

        cpu_time_delta = max(self.end_cpu_time - self.start_cpu_time, 0.0)
        duration = max(self.duration, 1e-6)
        avg_cpu_percent = round(
            (cpu_time_delta / duration) * 100 / self.monitor.cpu_core_count,
            2,
        )

        return {
            "duration_seconds": round(self.duration, 4),
            "start_cpu": self.start_stats["cpu_percent"],
            "end_cpu": self.end_stats["cpu_percent"],
            "avg_cpu_percent": avg_cpu_percent,
            "start_memory_mb": self.start_stats["memory_rss_mb"],
            "end_memory_mb": self.end_stats["memory_rss_mb"],
            "memory_delta_mb": round(self.end_stats["memory_rss_mb"] - self.start_stats["memory_rss_mb"], 2)
        }
