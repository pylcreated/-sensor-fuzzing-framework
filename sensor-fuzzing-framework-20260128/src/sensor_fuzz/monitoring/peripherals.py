"""Peripheral and environment monitoring placeholders."""

from __future__ import annotations

from typing import Dict, Optional
import threading
import time


class GpioMonitor:
    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    def read_state(self) -> Dict[str, bool]:
        return {"led": False, "relay": False}


class EnvMonitor:
    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    def read_env(self) -> Dict[str, float]:
        return {
            "temperature": 25.0,
            "humidity": 50.0,
            "light": 100.0,
            "vibration_hz": 0.0,
        }


class SystemMonitor:
    """System monitoring manager."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._gpio_monitor = GpioMonitor()
        self._env_monitor = EnvMonitor()

    def start(self) -> None:
        """Start system monitoring."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop system monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect GPIO and environment data
                gpio_state = self._gpio_monitor.read_state()
                env_data = self._env_monitor.read_env()

                # In a real implementation, this would update metrics
                # For now, just sleep
                time.sleep(5.0)
            except Exception:
                # Continue monitoring even if there's an error
                time.sleep(1.0)


# Global system monitor instance
_system_monitor: Optional[SystemMonitor] = None


def start_system_monitor() -> SystemMonitor:
    """Start the system monitor."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
        _system_monitor.start()
    return _system_monitor


def stop_system_monitor() -> None:
    """Stop the system monitor."""
    global _system_monitor
    if _system_monitor:
        _system_monitor.stop()
        _system_monitor = None
