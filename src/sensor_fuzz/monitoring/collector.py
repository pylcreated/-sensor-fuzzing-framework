"""Enhanced metrics and system stats collector."""

from __future__ import annotations

import threading
import time
from typing import Dict, Any, Optional

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

try:
    from prometheus_client import Gauge
except Exception:  # pragma: no cover

    class _Dummy:
        """类说明：封装  Dummy 的相关行为。"""
        def __init__(self, *_, **__):
            """方法说明：执行   init   相关逻辑。"""
            self._value = 0

        def set(self, v):
            """方法说明：执行 set 相关逻辑。"""
            self._value = v

        def _get(self):
            """方法说明：执行  get 相关逻辑。"""
            return self._value

    Gauge = _Dummy  # type: ignore

from sensor_fuzz.monitoring.metrics import (
    CPU_USAGE,
    MEMORY_USAGE,
    DISK_USAGE,
    ACTIVE_THREADS,
    UPTIME,
)


class SystemMonitor:
    """Enhanced system monitoring with historical data."""

    def __init__(self, collection_interval: float = 5.0):
        """方法说明：执行   init   相关逻辑。"""
        self.collection_interval = collection_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._history: Dict[str, list] = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "threads": [],
        }
        self._max_history = 100  # Keep last 100 readings

    def start(self) -> None:
        """Start monitoring thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self._collect_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(self.collection_interval)

    def _collect_metrics(self) -> None:
        """Collect current system metrics."""
        if psutil is None:
            self._set_dummy_values()
            return

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1.0)
        CPU_USAGE.set(cpu_percent)
        self._add_to_history("cpu", cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)
        self._add_to_history("memory", memory.used)

        # Disk usage
        disk = psutil.disk_usage("/")
        DISK_USAGE.set(disk.used)

        # Thread count
        threads = threading.active_count()
        ACTIVE_THREADS.set(threads)
        self._add_to_history("threads", threads)

    def _set_dummy_values(self) -> None:
        """Set dummy values when psutil is not available."""
        CPU_USAGE.set(0)
        MEMORY_USAGE.set(0)
        DISK_USAGE.set(0)
        ACTIVE_THREADS.set(threading.active_count())

    def _add_to_history(self, key: str, value: float) -> None:
        """Add value to history, maintaining max size."""
        history = self._history[key]
        history.append((time.time(), value))
        if len(history) > self._max_history:
            history.pop(0)

    def get_history(self, key: str, limit: int = 50) -> list:
        """Get historical data for a metric."""
        return self._history.get(key, [])[-limit:]

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        return {
            "cpu_percent": CPU_USAGE._get() if hasattr(CPU_USAGE, "_get") else 0,
            "memory_used": MEMORY_USAGE._get() if hasattr(MEMORY_USAGE, "_get") else 0,
            "disk_used": DISK_USAGE._get() if hasattr(DISK_USAGE, "_get") else 0,
            "active_threads": (
                ACTIVE_THREADS._get() if hasattr(ACTIVE_THREADS, "_get") else 0
            ),
            "uptime": UPTIME._get() if hasattr(UPTIME, "_get") else 0,
        }


# Global monitor instance
_monitor = SystemMonitor()


def collect_once() -> Dict[str, Any]:
    """Collect system metrics once and return current stats."""
    _monitor._collect_metrics()
    return _monitor.get_current_stats()


def start_system_monitor() -> SystemMonitor:
    """Start the system monitor."""
    _monitor.start()
    return _monitor


def stop_system_monitor() -> None:
    """Stop the system monitor."""
    _monitor.stop()


def get_system_stats() -> Dict[str, Any]:
    """Get current system statistics."""
    return _monitor.get_current_stats()


# Backward compatibility
SYSTEM_CPU = CPU_USAGE
SYSTEM_MEM = MEMORY_USAGE
DISK_FREE = DISK_USAGE
