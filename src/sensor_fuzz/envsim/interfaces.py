"""Environment simulation interfaces (skeleton)."""

from __future__ import annotations

from typing import Protocol


class EnvironmentSimulator(Protocol):
    """Protocol for environment simulation backends."""

    def set_temperature(self, value_c: float) -> None: ...

    def set_light_intensity(self, lux: float) -> None: ...

    def set_vibration(self, freq_hz: float, amplitude: float) -> None: ...
