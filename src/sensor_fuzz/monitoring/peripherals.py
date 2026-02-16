"""外设监控模块：采集 GPIO 与环境数据并提供统一监控入口。"""

from __future__ import annotations

from typing import Dict, Optional
import threading
import time


class GpioMonitor:
    """GPIO 监控器：读取继电器/指示灯等外设状态。"""
    def __init__(self, provider: str = "mock") -> None:
        """初始化 GPIO 数据提供方。"""
        self.provider = provider

    def read_state(self) -> Dict[str, bool]:
        """读取当前 GPIO 状态。"""
        return {"led": False, "relay": False}


class EnvMonitor:
    """环境监控器：读取温湿度、光照、振动等环境信息。"""
    def __init__(self, provider: str = "mock") -> None:
        """初始化环境数据提供方。"""
        self.provider = provider

    def read_env(self) -> Dict[str, float]:
        """读取当前环境数据。"""
        return {
            "temperature": 25.0,
            "humidity": 50.0,
            "light": 100.0,
            "vibration_hz": 0.0,
        }


class SystemMonitor:
    """系统监控管理器：统一调度外设与环境采集。"""

    def __init__(self):
        """初始化监控线程与子监控器。"""
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._gpio_monitor = GpioMonitor()
        self._env_monitor = EnvMonitor()

    def start(self) -> None:
        """启动系统监控。"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止系统监控。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """循环采集外设与环境数据。"""
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
    """启动全局系统监控器。"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
        _system_monitor.start()
    return _system_monitor


def stop_system_monitor() -> None:
    """停止全局系统监控器。"""
    global _system_monitor
    if _system_monitor:
        _system_monitor.stop()
        _system_monitor = None
