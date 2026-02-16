"""系统指标采集模块：采集 CPU/内存/线程等运行数据。"""

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
        """Prometheus 不可用时的占位 Gauge 实现。"""
        def __init__(self, *_, **__):
            """初始化占位值。"""
            self._value = 0

        def set(self, v):
            """设置占位指标值。"""
            self._value = v

        def _get(self):
            """读取占位指标值。"""
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
    """系统监控器：周期采集指标并保留历史窗口。"""

    def __init__(self, collection_interval: float = 5.0):
        """初始化采样间隔、线程状态与历史缓存。"""
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
        """启动后台监控线程。"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止监控线程。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """监控主循环：采集失败时自动容错重试。"""
        while self._running:
            try:
                self._collect_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(self.collection_interval)

    def _collect_metrics(self) -> None:
        """采集当前系统指标并更新 Prometheus 指标。"""
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
        """当 psutil 不可用时写入降级指标。"""
        CPU_USAGE.set(0)
        MEMORY_USAGE.set(0)
        DISK_USAGE.set(0)
        ACTIVE_THREADS.set(threading.active_count())

    def _add_to_history(self, key: str, value: float) -> None:
        """记录历史采样并限制历史长度。"""
        history = self._history[key]
        history.append((time.time(), value))
        if len(history) > self._max_history:
            history.pop(0)

    def get_history(self, key: str, limit: int = 50) -> list:
        """获取指定指标最近历史数据。"""
        return self._history.get(key, [])[-limit:]

    def get_current_stats(self) -> Dict[str, Any]:
        """读取当前系统统计快照。"""
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
    """执行一次即时采集并返回结果。"""
    _monitor._collect_metrics()
    return _monitor.get_current_stats()


def start_system_monitor() -> SystemMonitor:
    """启动全局系统监控实例。"""
    _monitor.start()
    return _monitor


def stop_system_monitor() -> None:
    """停止全局系统监控实例。"""
    _monitor.stop()


def get_system_stats() -> Dict[str, Any]:
    """读取全局系统监控的当前状态。"""
    return _monitor.get_current_stats()


# Backward compatibility
SYSTEM_CPU = CPU_USAGE
SYSTEM_MEM = MEMORY_USAGE
DISK_FREE = DISK_USAGE
