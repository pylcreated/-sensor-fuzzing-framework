"""Voltage/current guard placeholder with cut-off decision."""

from __future__ import annotations

from typing import Dict, Tuple


class VoltageCurrentGuard:
    def __init__(self, max_voltage: float = 15.0, max_current: float = 0.5) -> None:
        self.max_voltage = max_voltage
        self.max_current = max_current

    def evaluate(self, reading: Dict[str, float]) -> Tuple[bool, str]:
        voltage = reading.get("voltage", 0.0)
        current = reading.get("current", 0.0)
        if voltage >= self.max_voltage or current >= self.max_current:
            return True, "cut-off"
        return False, "ok"
