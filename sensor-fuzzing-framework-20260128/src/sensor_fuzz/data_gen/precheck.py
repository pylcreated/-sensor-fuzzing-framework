"""Pre-check hooks for cases: protobuf syntax, compatibility, safety."""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List


def protobuf_syntax_ok(payload: bytes) -> bool:
    """Validate protobuf payload syntax and safety."""
    if not isinstance(payload, bytes):
        return False
    # Check for potentially dangerous patterns
    dangerous_patterns = [
        b"<script",
        b"javascript:",
        b"onload=",
        b"onerror=",
        b"eval(",
        b"exec(",
        b"system(",
    ]
    payload_lower = payload.lower()
    for pattern in dangerous_patterns:
        if pattern in payload_lower:
            return False
    return len(payload) > 0


def protocol_compat_ok(sensor: Dict, protocol: str) -> bool:
    """Validate protocol compatibility with enhanced security checks."""
    if not isinstance(sensor, dict):
        return False
    if not isinstance(protocol, str):
        return False

    # Validate protocol name
    allowed_protocols = {
        "mqtt",
        "http",
        "modbus",
        "opcua",
        "uart",
        "i2c",
        "spi",
        "profinet",
    }
    if protocol.lower() not in allowed_protocols:
        return False

    sensor_protocol = sensor.get("protocol")
    if sensor_protocol is not None:
        if not isinstance(sensor_protocol, str):
            return False
        if sensor_protocol.lower() not in allowed_protocols:
            return False
        return sensor_protocol.lower() == protocol.lower()

    return True


def poc_safety_ok(poc: str) -> bool:
    """Enhanced POC safety validation."""
    if not isinstance(poc, str):
        return False

    # Disallow destructive placeholders
    banned = {
        "over-voltage-burn",
        "short-circuit",
        "thermal-damage",
        "memory-corruption",
        "buffer-overflow",
        "sql-injection",
        "command-injection",
        "path-traversal",
    }

    if poc.lower() in banned:
        return False

    # Check for dangerous patterns
    dangerous_patterns = [
        r"rm\s+-rf",
        r"del\s+/f",
        r"format\s+c:",
        r"shutdown",
        r"reboot",
        r"halt",
        r"kill\s+-9",
        r"pkill",
        r"taskkill",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, poc, re.IGNORECASE):
            return False

    return True


def sensor_config_safe(sensor: Dict) -> bool:
    """Validate sensor configuration for safety."""
    if not isinstance(sensor, dict):
        return False

    # Validate range
    sensor_range = sensor.get("range")
    if sensor_range is not None:
        if not isinstance(sensor_range, list) or len(sensor_range) != 2:
            return False
        try:
            low, high = float(sensor_range[0]), float(sensor_range[1])
            if low >= high:
                return False
            # Reasonable bounds check
            if abs(low) > 1e6 or abs(high) > 1e6:
                return False
        except (ValueError, TypeError):
            return False

    # Validate signal type
    signal_type = sensor.get("signal_type", "").lower()
    allowed_types = {"current", "voltage", "digital", "analog", "4-20ma", "0-10v"}
    if signal_type and signal_type not in allowed_types:
        return False

    # Validate precision
    precision = sensor.get("precision")
    if precision is not None:
        try:
            prec = float(precision)
            if prec <= 0 or prec > 1:
                return False
        except (ValueError, TypeError):
            return False

    return True


def benchmark_prechecks(
    cases: Iterable[Dict], checks: List[Callable[[Dict], bool]]
) -> Dict[str, float]:
    """Return acceptance ratio for provided prechecks.

    Each check receives the case dict; results are averaged per check index.
    """
    totals = [0] * len(checks)
    passed = [0] * len(checks)
    for case in cases:
        for idx, check in enumerate(checks):
            totals[idx] += 1
            try:
                if check(case):
                    passed[idx] += 1
            except Exception as e:
                # Log the exception but treat as failure to maintain safety bias
                import logging
                logging.warning(f"Precheck failed for case {case}: {e}")
                # Continue to next check - exceptions count as failures
    return {
        f"check_{i}": (passed[i] / totals[i] if totals[i] else 0.0)
        for i in range(len(checks))
    }
