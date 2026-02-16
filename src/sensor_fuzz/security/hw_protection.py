"""硬件保护模块：根据电压电流阈值判定是否触发保护。"""

from __future__ import annotations

from typing import Dict, Tuple


class VoltageCurrentGuard:
    """电压电流保护器：超阈值时给出切断建议。"""
    def __init__(self, max_voltage: float = 15.0, max_current: float = 0.5) -> None:
        """初始化最大允许电压与电流阈值。"""
        self.max_voltage = max_voltage
        self.max_current = max_current

    def evaluate(self, reading: Dict[str, float]) -> Tuple[bool, str]:
        """评估当前读数，返回 (是否切断, 状态标识)。"""
        voltage = reading.get("voltage", 0.0)
        current = reading.get("current", 0.0)
        if voltage >= self.max_voltage or current >= self.max_current:
            return True, "cut-off"
        return False, "ok"
