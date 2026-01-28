"""General anomaly value generation."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List
import json

from sensor_fuzz.data_gen.precheck import sensor_config_safe

NON_NUMERIC = ["NaN", "INF", "-INF", "", None, "特殊字符!@#"]


def generate_anomaly_values(
    sensor: Dict, overshoot_ratio: float = 0.1
) -> List[Dict[str, Any]]:
    """Generate anomaly values for sensor testing."""
    return _generate_anomaly_values_cached(
        json.dumps(sensor, sort_keys=True, default=str), overshoot_ratio
    )


@lru_cache(maxsize=128)
def _generate_anomaly_values_cached(
    sensor_json: str, overshoot_ratio: float = 0.1
) -> List[Dict[str, Any]]:
    """Cached version of anomaly value generation."""
    sensor = json.loads(sensor_json)

    # Security check
    if not sensor_config_safe(sensor):
        return []
    rng = sensor.get("range", [0, 1])
    low, high = float(rng[0]), float(rng[1])
    span = abs(high - low)
    overshoot = span * overshoot_ratio
    anomalies: List[Dict[str, Any]] = []
    anomalies.append({"value": high + overshoot, "desc": "over-high"})
    anomalies.append({"value": low - overshoot, "desc": "over-low"})
    anomalies.append({"value": None, "desc": "null"})
    anomalies.append({"value": "", "desc": "empty-string"})
    anomalies.append({"value": high, "desc": "duplicate-upper"})
    anomalies.extend({"value": v, "desc": "non-numeric"} for v in NON_NUMERIC)

    signal_type = (sensor.get("signal_type") or "").lower()
    if signal_type in {"current", "4-20ma"}:
        anomalies.extend(
            [
                {"value": 4.0, "desc": "stuck-low-4ma"},
                {"value": 20.0, "desc": "stuck-high-20ma"},
                {"value": 0.0, "desc": "underflow-current"},
            ]
        )
    if signal_type in {"voltage", "0-10v"}:
        anomalies.extend(
            [
                {"value": 0.0, "desc": "stuck-low-0v"},
                {"value": 10.0, "desc": "stuck-high-10v"},
                {"value": -1.0, "desc": "underflow-voltage"},
            ]
        )
    return anomalies
