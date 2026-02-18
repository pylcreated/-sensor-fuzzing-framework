"""Environment simulation runtime with scenario replay and noise injection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from random import Random
from typing import Dict, Iterable, List, Optional


@dataclass
class EnvironmentState:
    """Current simulated environment state."""

    timestamp_s: float
    temperature_c: float
    light_lux: float
    vibration_freq_hz: float
    vibration_amplitude: float


class SimulatedEnvironment:
    """In-process environment simulator for repeatable experiments."""

    def __init__(
        self,
        *,
        base_temperature_c: float = 25.0,
        base_light_lux: float = 300.0,
        base_vibration_freq_hz: float = 0.0,
        base_vibration_amplitude: float = 0.0,
        seed: Optional[int] = 2026,
    ) -> None:
        self._random = Random(seed)
        self._time_s = 0.0
        self._temperature_c = base_temperature_c
        self._light_lux = base_light_lux
        self._vibration_freq_hz = base_vibration_freq_hz
        self._vibration_amplitude = base_vibration_amplitude

    def set_temperature(self, value_c: float) -> None:
        self._temperature_c = float(value_c)

    def set_light_intensity(self, lux: float) -> None:
        self._light_lux = float(lux)

    def set_vibration(self, freq_hz: float, amplitude: float) -> None:
        self._vibration_freq_hz = float(freq_hz)
        self._vibration_amplitude = float(amplitude)

    def advance(self, dt_s: float = 1.0) -> None:
        self._time_s += max(float(dt_s), 0.0)

    def snapshot(
        self,
        *,
        temperature_noise_std: float = 0.0,
        light_noise_std: float = 0.0,
        vibration_noise_std: float = 0.0,
    ) -> Dict[str, float]:
        """Return an observable sample with optional Gaussian noise."""
        state = EnvironmentState(
            timestamp_s=self._time_s,
            temperature_c=self._temperature_c,
            light_lux=self._light_lux,
            vibration_freq_hz=self._vibration_freq_hz,
            vibration_amplitude=self._vibration_amplitude,
        )
        sampled = asdict(state)
        if temperature_noise_std > 0:
            sampled["temperature_c"] += self._random.gauss(0.0, temperature_noise_std)
        if light_noise_std > 0:
            sampled["light_lux"] += self._random.gauss(0.0, light_noise_std)
        if vibration_noise_std > 0:
            sampled["vibration_amplitude"] += self._random.gauss(0.0, vibration_noise_std)
        return sampled

    def run_scenario(
        self,
        steps: Iterable[Dict[str, float]],
        *,
        default_dt_s: float = 1.0,
        temperature_noise_std: float = 0.0,
        light_noise_std: float = 0.0,
        vibration_noise_std: float = 0.0,
    ) -> List[Dict[str, float]]:
        """Replay scenario steps and return sampled timeline."""
        timeline: List[Dict[str, float]] = []
        for step in steps:
            if "temperature_c" in step:
                self.set_temperature(float(step["temperature_c"]))
            if "light_lux" in step:
                self.set_light_intensity(float(step["light_lux"]))
            if "vibration_freq_hz" in step or "vibration_amplitude" in step:
                self.set_vibration(
                    float(step.get("vibration_freq_hz", self._vibration_freq_hz)),
                    float(step.get("vibration_amplitude", self._vibration_amplitude)),
                )

            self.advance(float(step.get("dt_s", default_dt_s)))
            timeline.append(
                self.snapshot(
                    temperature_noise_std=temperature_noise_std,
                    light_noise_std=light_noise_std,
                    vibration_noise_std=vibration_noise_std,
                )
            )
        return timeline
