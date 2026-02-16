"""Boundary generation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List
import json

from sensor_fuzz.data_gen.precheck import sensor_config_safe


@dataclass
class BoundaryCase:
    """类说明：封装 BoundaryCase 的相关行为。"""
    value: float
    desc: str


def generate_boundary_cases(sensor: Dict, tolerance: float = 0.001) -> List[Dict]:
    """Generate boundary cases within ±tolerance of sensor range.

    tolerance=0.001 corresponds to ±0.1% as要求.
    # Adds analog guardrails for 4-20mA / 0-10V by injecting slight under/overflow.
    """
    return _generate_boundary_cases_cached(
        json.dumps(sensor, sort_keys=True, default=str), tolerance
    )


@lru_cache(maxsize=128)
def _generate_boundary_cases_cached(
    sensor_json: str, tolerance: float = 0.001
) -> List[Dict]:
    """Cached version of boundary case generation."""
    sensor = json.loads(sensor_json)

    # Security check
    if not sensor_config_safe(sensor):
        return []
    rng = sensor.get("range", [0, 1])
    low, high = float(rng[0]), float(rng[1])
    delta_low = max(abs(low) * tolerance, tolerance)
    delta_high = max(abs(high) * tolerance, tolerance)
    cases = [
        BoundaryCase(low - delta_low, "lower-bound-minus"),
        BoundaryCase(low, "lower-bound"),
        BoundaryCase(high, "upper-bound"),
        BoundaryCase(high + delta_high, "upper-bound-plus"),
    ]

    signal_type = (sensor.get("signal_type") or "").lower()
    if signal_type in {"current", "4-20ma"}:
        cases.extend(
            [
                BoundaryCase(3.8, "underflow-4ma"),
                BoundaryCase(20.5, "overflow-20ma"),
            ]
        )
    if signal_type in {"voltage", "0-10v"}:
        cases.extend(
            [
                BoundaryCase(-0.1, "underflow-0v"),
                BoundaryCase(10.5, "overflow-10v"),
            ]
        )

    freq = sensor.get("anomaly_freq", 1)
    result = []
    for c in cases:
        # Use pooled objects to reduce memory allocation
        case_dict = _get_case_from_pool()
        case_dict.update({"value": c.value, "desc": c.desc, "freq": freq})
        result.append(case_dict)
    return result


def _get_case_from_pool():
    """Get a case dict from pool, creating if needed."""
    try:
        from sensor_fuzz.engine.memory_pool import CaseObjectPool
        if not hasattr(_get_case_from_pool, '_pool'):
            _get_case_from_pool._pool = CaseObjectPool(max_size=200, timeout=600.0)
        return _get_case_from_pool._pool.acquire()
    except ImportError:
        # Fallback if pool not available
        return {}
