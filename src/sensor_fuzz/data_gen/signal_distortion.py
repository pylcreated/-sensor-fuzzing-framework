"""Analog signal distortion scenarios for 4-20mA and 0-10V."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List
import json

from sensor_fuzz.data_gen.precheck import sensor_config_safe


def distort_signal(sensor: Dict) -> List[Dict]:
    """Generate signal distortion scenarios for analog sensors."""
    return _distort_signal_cached(json.dumps(sensor, sort_keys=True, default=str))


@lru_cache(maxsize=64)
def _distort_signal_cached(sensor_json: str) -> List[Dict]:
    """Cached version of signal distortion generation."""
    sensor = json.loads(sensor_json)

    # Security check
    if not sensor_config_safe(sensor):
        return []
    signal_type = sensor.get("signal_type", "current")
    cases: List[Dict] = []
    if signal_type in {"current", "4-20mA"}:
        cases.extend(
            [
                {"desc": "drift", "value": 22.0},
                {"desc": "drop", "value": 3.0},
                {"desc": "noise", "value": 12.0, "noise_rms": 0.5},
            ]
        )
    if signal_type in {"voltage", "0-10V"}:
        cases.extend(
            [
                {"desc": "drift", "value": 10.5},
                {"desc": "drop", "value": -0.5},
                {"desc": "noise", "value": 5.0, "noise_rms": 0.2},
            ]
        )
    return cases
